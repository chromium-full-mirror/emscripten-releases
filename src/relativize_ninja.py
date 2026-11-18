#!/usr/bin/env python3

#   Copyright 2026 WebAssembly Community Group participants
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

r"""Post-process CMake's generated Ninja files on Windows for Reclient RBE builds.

Why this exists:
  Untrusted RBE pools (used by Windows trybots and local developer builds) execute
  Windows `clang-cl` actions on Linux cross-compile containers (`OSFamily=Linux`,
  `canonicalize_working_dir=true`), whereas CI uses native Windows RBE workers.
  Unlike POSIX hosts, Windows drive-letter `exec_root` paths (`C:\...`) cannot be
  mounted via `InputRootAbsolutePath` on Linux containers, and remote Linux
  `clang-cl` cannot resolve `C:\...` absolute paths or backslash output separators
  emitted by CMake's Ninja generator (see b/309009233).

What it does:
  Rewrites C/C++ compile rules in `<build_dir>/CMakeFiles/rules.ninja` and compile
  stanzas in `<build_dir>/build.ninja` after CMake generation so Ninja invokes
  `rewrapper.exe` directly without a per-compile wrapper process:
  - Relativizes the compiler binary path with `\` so both remote workers and local
    Windows fallback (`CreateProcess`) work.
  - Relativizes `exec_root`-prefixed input, `-I`, `-imsvc`, and `/winsysroot` paths
    to `<build_dir>` using `/`, while leaving `-D`/`/D`/`-U`/`/U` macros and
    `LAUNCHER` (`rewrapper.exe` flags) untouched.
  - Emits explicit `OUT_POSIX` and `IN_POSIX` stanza variables using `/` so Ninja's
    `Node::slash_bits_` cannot reintroduce `\` into `/Fo` or source arguments.
  - Hooks `rule RERUN_CMAKE` so automatic Ninja CMake regenerations stay relativized.
"""

import functools
import ntpath
import os
import re
import sys

# Matches CMake's Ninja build edge header for C/C++ compilation, e.g.:
#   build dir\foo.cpp.obj: CXX_COMPILER__tgt_unscanned_Release C$:\...\foo.cpp || deps
# Groups: (1) "build ", (2) outputs, (3) ": <C|CXX>_COMPILER__... ", (4) inputs + deps.
COMPILE_BUILD_RE = re.compile(
    r'^(build\s+)(.+?)(:\s+(?:C|CXX)_COMPILER__\S+\s+)(.+)$',
)

# Splits the right-hand side of a Ninja `build` header at the first `|`, `||`, or
# `|@` delimiter separating explicit inputs from implicit (`|`), order-only (`||`),
# or validation (`|@`) dependencies, preserving whitespace + delimiter in group 1.
NINJA_DEP_SPLIT_RE = re.compile(r'(\s+\|(?:\||@)?\s+)')

# Splits space-separated path tokens on a Ninja `build` header line while keeping
# Ninja-escaped spaces (`$ `) inside a single path token together.
NINJA_PATH_SPLIT_RE = re.compile(r'(?<!\$)\s+')

# Tokenizes a compiler `INCLUDES` or `FLAGS` line into alternating whitespace runs
# and single CLI arguments, keeping `"..."` quoted spans (including escaped `\"`
# quotes and spaces inside quotes, e.g. `-I"C:\My Dir"`) attached to their flag.
FLAG_TOKEN_RE = re.compile(r'\s+|(?:[^\s"]+|"(?:\\"|[^"])*")+')

# Matches either a double-quoted span `"..."` (group 1 = inner text, where spaces
# are literal path characters) or an unquoted non-whitespace run (group 2).
SPAN_RE = re.compile(r'"((?:\\"|[^"])*)"|([^\s"]+)')

# Matches one or more trailing backslashes at the end of a path so they can be
# doubled before a closing `"` for Win32 CommandLineToArgvW (e.g. `"D:\"` -> `"D:\\"`).
TRAILING_BACKSLASHES_RE = re.compile(r'(\\+)$')

# Matches the trailing `-- $in` source-file placeholder at the end of CMake's
# `clang-cl` compile rule command so it can be replaced with `-- $IN_POSIX`.
RULE_IN_RE = re.compile(r'(\s--\s)\$in(\s*)$')


def quote_win_arg(path):
    escaped = TRAILING_BACKSLASHES_RE.sub(r'\1\1', path)
    return f'"{escaped}"'


def compile_exec_root_re(drive, tail_parts):
    # Matches `exec_root` (group 1) followed by an optional subpath under it
    # (group 2) within an unescaped path or quoted/unquoted argument span:
    # - When `exec_root` has directory components (e.g. `C:\src\emr`), group 2
    #   matches either `[\\/]<subpath>` or a path-boundary end (`$`, `"`, `;`, `|`, `=`)
    #   so sibling prefixes like `C:\src\emr2` are not matched.
    # - When `exec_root` is a drive root (e.g. `D:\`, `tail_parts == []`), a
    #   positive lookahead `(?=[\\/])` ensures `D:` is followed by a slash without
    #   consuming it, so group 2 captures `\subpath` (or `\` for the root itself)
    #   and drive-relative paths like `D:foo.cpp` are ignored.
    sep_pat = r'[\\/]'
    drive_pat = rf'{re.escape(drive[0])}:'
    if tail_parts:
        parts_pat = sep_pat.join(re.escape(p) for p in tail_parts)
        root_pat = rf'{drive_pat}{sep_pat}{parts_pat}'
        sub_pat = rf'(?:{sep_pat}[^";|=]*|(?=$|[";|=]))'
    else:
        root_pat = rf'{drive_pat}(?={sep_pat})'
        sub_pat = rf'{sep_pat}[^";|=]*'
    return re.compile(rf'({root_pat})({sub_pat})', re.IGNORECASE)


def rewrite_spans(text, path_re, rel_fn):
    def replace_span(m):
        quoted, unquoted = m.groups()
        if quoted is not None:
            rewritten = path_re.sub(lambda pm: rel_fn(pm.group(2)), quoted)
            return f'"{rewritten}"'
        rewritten = path_re.sub(lambda pm: rel_fn(pm.group(2)), unquoted)
        if ' ' in rewritten:
            return f'"{rewritten}"'
        return rewritten

    return SPAN_RE.sub(replace_span, text)


def make_path_rewriter(build_dir, exec_root):
    build_dir_abs = ntpath.abspath(build_dir)
    drive, tail = ntpath.splitdrive(ntpath.abspath(exec_root))
    drive_root = drive + '\\'
    tail_parts = [p for p in tail.strip('\\/').split('\\') if p]
    path_re = compile_exec_root_re(drive, tail_parts)

    @functools.cache
    def rel_posix(raw_subpath):
        sub = raw_subpath.lstrip('\\/').replace('/', '\\')
        full = ntpath.join(drive_root, *tail_parts, sub) if sub else ntpath.join(
            drive_root, *tail_parts)
        rel = ntpath.relpath(full, build_dir_abs).replace('\\', '/')
        return rel or '.'

    @functools.cache
    def rel_win(raw_subpath):
        sub = raw_subpath.lstrip('\\/').replace('/', '\\')
        full = ntpath.join(drive_root, *tail_parts, sub) if sub else ntpath.join(
            drive_root, *tail_parts)
        return ntpath.relpath(full, build_dir_abs)

    def rewrite_posix(text):
        return rewrite_spans(text, path_re, rel_posix)

    def rewrite_win(text):
        return rewrite_spans(text, path_re, rel_win)

    def rewrite_plain_posix(plain_path):
        return path_re.sub(lambda m: rel_posix(m.group(2)), plain_path).replace('\\', '/')

    return rewrite_posix, rewrite_win, rewrite_plain_posix


def format_var_paths(build_paths):
    """Convert Ninja build-edge path tokens into shell-quoted command variable values.

    In a Ninja `build` header, spaces inside paths are escaped as `$ `, whereas
    plain variables interpolated into `command = ...` are split by the shell unless
    quoted. Split on unescaped whitespace, unescape `$ `, and quote paths with spaces.
    """
    tokens = NINJA_PATH_SPLIT_RE.split(build_paths.strip())
    formatted = []
    for tok in tokens:
        if not tok:
            continue
        unescaped = tok.replace('$ ', ' ').replace('$:', ':')
        formatted.append(f'"{unescaped}"' if ' ' in unescaped else unescaped)
    return ' '.join(formatted)


def rewrite_build_header_inputs(raw_inputs, rewrite_plain_posix):
    """Rewrite explicit input paths on a Ninja `build` header line.

    Unescapes Ninja path tokens (`$ ` -> ` `, `$:` -> `:`), relativizes paths under
    `exec_root` to `/` paths, and returns `(header_inputs, in_posix_var)` where
    `header_inputs` is re-escaped for the `build` line and `in_posix_var` is
    shell-quoted for `IN_POSIX`.
    """
    tokens = NINJA_PATH_SPLIT_RE.split(raw_inputs.strip())
    header_parts = []
    var_parts = []
    for tok in tokens:
        if not tok:
            continue
        plain = tok.replace('$ ', ' ').replace('$:', ':')
        rel = rewrite_plain_posix(plain)
        header_parts.append(rel.replace(':', '$:').replace(' ', '$ '))
        var_parts.append(f'"{rel}"' if ' ' in rel else rel)
    return ' '.join(header_parts), ' '.join(var_parts)


def rewrite_flags_tokens(line_prefix, value, rewrite_posix, normalize_slashes=False):
    # Preserve -D / /D / -U / /U macro definitions untouched so string literal
    # paths (e.g. unit test data paths) are not altered.
    out = [line_prefix]
    skip_next = False
    for tok in FLAG_TOKEN_RE.findall(value):
        if tok[0].isspace():
            out.append(tok)
            continue
        if skip_next:
            out.append(tok)
            skip_next = False
            continue
        if tok in {'-D', '/D', '-U', '/U'}:
            out.append(tok)
            skip_next = True
            continue
        if tok.lstrip('"').startswith(('-D', '/D', '-U', '/U')):
            out.append(tok)
            continue
        rewritten = rewrite_posix(tok)
        if normalize_slashes:
            rewritten = rewritten.replace('\\', '/')
        out.append(rewritten)
    return ''.join(out)


def rewrite_rules_ninja(rules_path, build_dir, exec_root, script_path):
    if not os.path.isfile(rules_path):
        return
    _rewrite_posix, rewrite_win, _rewrite_plain = make_path_rewriter(build_dir, exec_root)

    with open(rules_path, encoding='utf-8') as f:
        lines = f.readlines()

    out_lines = []
    current_rule = ''
    for line in lines:
        if line.startswith('rule '):
            current_rule = line.removeprefix('rule ').strip()
            out_lines.append(line)
            continue

        new_line = line
        if current_rule.startswith(('C_COMPILER__', 'CXX_COMPILER__')):
            if line.startswith('  command = '):
                # Relativize the compiler binary path using Windows backslashes so
                # local fallback works, and use $OUT_POSIX / $IN_POSIX so Ninja's
                # Node::slash_bits_ cannot emit backslashes in /Fo or source paths
                # when a node was referenced with '\' earlier in build.ninja.
                new_line = rewrite_win(line).replace('/Fo$out ', '/Fo$OUT_POSIX ')
                new_line = RULE_IN_RE.sub(r'\1$IN_POSIX\2', new_line)
        elif current_rule == 'RERUN_CMAKE' and line.startswith('  command = '):
            # Ninja invokes RERUN_CMAKE automatically when CMakeLists.txt files
            # change, which overwrites build.ninja and rules.ninja with fresh
            # absolute Windows paths. Chain relativize_ninja.py onto RERUN_CMAKE
            # so bare `ninja` regenerations stay relativized before Ninja reloads.
            if 'relativize_ninja.py' not in line:
                nl = '\r\n' if line.endswith('\r\n') else '\n'
                orig_cmd = line.removeprefix('  command = ').rstrip('\r\n')
                hook_cmd = ' '.join([
                    quote_win_arg(sys.executable),
                    quote_win_arg(script_path),
                    quote_win_arg(ntpath.abspath(build_dir)),
                    quote_win_arg(ntpath.abspath(exec_root)),
                ]).replace('$', '$$')
                new_line = (
                    r'  command = C:\Windows\system32\cmd.exe /S /C '
                    f'"{orig_cmd} && {hook_cmd}"{nl}'
                )

        out_lines.append(new_line)

    with open(rules_path, 'w', encoding='utf-8', newline='') as f:
        f.writelines(out_lines)


def rewrite_compile_header(line, m, rewrite_plain_posix):
    r"""Rewrite a C/C++ `build` header line and emit OUT_POSIX / IN_POSIX variables.

    Relativizes explicit source inputs (before any `|` / `||` implicit or order-only
    dependencies) to `build_dir`-relative `/` paths, normalizes output slashes to `/`,
    and binds `OUT_POSIX` and `IN_POSIX` for the compile command. Explicit variables
    are used instead of `$out` / `$in` because on Windows Ninja records each `Node`'s
    slash style on its first appearance in `build.ninja` (`Node::slash_bits_`), which
    would expand `$out` with `\` if an `.obj` (e.g. from an `OBJECT` library) was
    listed earlier in a link line.
    """
    prefix, outputs, rule_part, rest = m.groups()
    outputs_posix = outputs.replace('\\', '/')
    dep_split = NINJA_DEP_SPLIT_RE.split(rest, maxsplit=1)
    explicit_ins, in_posix_var = rewrite_build_header_inputs(
        dep_split[0], rewrite_plain_posix)
    tail = ''.join(dep_split[1:])
    nl = '\r\n' if line.endswith('\r\n') else '\n'
    return [
        f'{prefix}{outputs_posix}{rule_part}{explicit_ins}{tail}{nl}',
        f'  OUT_POSIX = {format_var_paths(outputs_posix)}{nl}',
        f'  IN_POSIX = {in_posix_var}{nl}',
    ]


def rewrite_compile_stanza_line(line, rewrite_posix):
    """Rewrite an indented variable line inside a C/C++ compile stanza.

    Relativizes include/compiler flags and normalizes PDB output slashes to `/` for
    remote Linux cross-workers. Strips any prior `OUT_POSIX` / `IN_POSIX` lines so
    re-running this script is idempotent, and leaves `LAUNCHER` untouched because
    local `rewrapper.exe` requires absolute `-cfg` and `-exec_root` paths.
    """
    if line.startswith(('  OUT_POSIX = ', '  IN_POSIX = ')):
        return None
    if line.startswith('  INCLUDES = '):
        return rewrite_flags_tokens(
            '  INCLUDES = ',
            line.removeprefix('  INCLUDES = '),
            rewrite_posix,
            normalize_slashes=True,
        )
    if line.startswith('  FLAGS = '):
        return rewrite_flags_tokens(
            '  FLAGS = ', line.removeprefix('  FLAGS = '), rewrite_posix)
    if line.startswith('  TARGET_COMPILE_PDB = '):
        pdb = rewrite_posix(line.removeprefix('  TARGET_COMPILE_PDB = ')).replace('\\', '/')
        return f'  TARGET_COMPILE_PDB = {pdb}'
    return line


def rewrite_build_ninja(build_ninja_path, build_dir, exec_root):
    rewrite_posix, _rewrite_win, rewrite_plain_posix = make_path_rewriter(
        build_dir, exec_root)
    cached_rewrite_stanza_line = functools.cache(
        lambda s: rewrite_compile_stanza_line(s, rewrite_posix),
    )

    with open(build_ninja_path, encoding='utf-8') as f:
        lines = f.readlines()

    out_lines = []
    in_compile_stanza = False
    for line in lines:
        if line.startswith('build '):
            m = COMPILE_BUILD_RE.match(line.rstrip('\r\n')) if '_COMPILER__' in line else None
            if m:
                in_compile_stanza = True
                out_lines.extend(rewrite_compile_header(line, m, rewrite_plain_posix))
                continue
            in_compile_stanza = False
            out_lines.append(line)
            continue

        if not line.startswith('  '):
            in_compile_stanza = False
            out_lines.append(line)
            continue

        if in_compile_stanza:
            rewritten = cached_rewrite_stanza_line(line)
            if rewritten is not None:
                out_lines.append(rewritten)
        else:
            out_lines.append(line)

    with open(build_ninja_path, 'w', encoding='utf-8', newline='') as f:
        f.writelines(out_lines)


def relativize_ninja_dir(build_dir, exec_root):
    build_ninja_path = os.path.join(build_dir, 'build.ninja')
    if not os.path.isfile(build_ninja_path):
        raise FileNotFoundError(f'build.ninja not found in {build_dir}')
    script_path = os.path.abspath(__file__)
    rewrite_rules_ninja(
        os.path.join(build_dir, 'CMakeFiles', 'rules.ninja'),
        build_dir,
        exec_root,
        script_path,
    )
    rewrite_build_ninja(
        build_ninja_path,
        build_dir,
        exec_root,
    )


def main():
    if len(sys.argv) != 3:
        print(f'Usage: {sys.argv[0]} <build_dir> <exec_root>', file=sys.stderr)
        return 1
    relativize_ninja_dir(sys.argv[1], sys.argv[2])
    return 0


if __name__ == '__main__':
    sys.exit(main())
