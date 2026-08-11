#!/usr/bin/env python3

#   Copyright 2015 WebAssembly Community Group participants
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

import argparse
import os
import re
import subprocess
import sys

script_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(script_dir)

top_comment = '''\
#
# IMPORTANT: This file is a copy the DEPS file that exists in order to trigger
# the release builds to produce an official LTO build to be part of a release.
# Each time this file changes the builders will produce an LTO SDK build.
#
# IMPORTANT: This file is (mostly) updated by running the
# src/create_release_candidate.py script which will overwrite with a copy of the
# DEPS file from a particular point in time. See src/create_release_candidate.py
# for more on this.
#
# VERSION: %s
'''


def run(cmd, capture_output=False):
    try:
        return subprocess.run(cmd, cwd=root_dir, capture_output=capture_output,
                              text=True, check=True).stdout
    except subprocess.CalledProcessError as e:
        print('Command failed: ' + ' '.join(cmd))
        print(e.stdout)
        print(e.stderr)
        raise


def modify_deps_file(content, version):
    # Insert `top_comment` after the initial copyright comment
    pos = content.find('\n\n')
    assert pos != -1
    pos += 1
    return content[:pos] + (top_comment % version) + content[pos:]


def create_cl(source_rev, tag, dry_run):
    if run(['git', 'status', '--porcelain', '--untracked-files=no']):
        print('tree is not clean')
        return 1

    # Copy DEPS from source_rev to DEPS.tagged_release
    deps = run(['git', 'show', f'{source_rev}:DEPS'], capture_output=True)
    deps = modify_deps_file(deps, tag)
    with open(os.path.join(root_dir, 'DEPS.tagged-release'), 'w') as f:
        f.write(deps)

    if dry_run:
        return

    # Create a new git branch
    branch_name = f'version_{tag}_rc'
    run(['git', 'checkout', '-b', branch_name])

    run(['git', 'add', '-u', 'DEPS.tagged-release'])
    message = f'Version {tag} RC\n\nDEPS from revision {source_rev}\n'
    message += 'This CL was created by src/create_release_candidate.py'
    run(['git', 'commit', '-m', message])
    reviewers = 'dschuff@chromium.org,sbc@chromium.org,azakai@google.com'
    run(['git', 'cl', 'upload', '--send-mail', '-r', reviewers])


def parse_version():
    deps = open(os.path.join(root_dir, 'DEPS.tagged-release')).read()
    match = re.search(r"^# VERSION: (.*)$", deps, re.MULTILINE)
    if not match:
        return None
    return match.group(1)


def main(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument('-r', '--revision', help='git revision to use for release')
    parser.add_argument('-n', '--dry-run', action='store_true',
                        help='update DEPS.tagged_release but do not commit changes or upload them')
    parser.add_argument('version', help='emscripten version (e.g. 3.1.66)', nargs='?')
    args = parser.parse_args(argv)
    if not args.version:
        version = parse_version()
        if not version:
            print('no version specified and failed to parse version from DEPS.tagged_release')
            return 1
        version = [int(v) for v in version.split('.')]
        version[-1] += 1
        args.version = '.'.join(str(v) for v in version)
    tag = args.version
    source_rev = args.revision
    if not source_rev:
        source_rev = run(['git', 'rev-parse', 'HEAD'], True).strip()
    create_cl(source_rev, tag, args.dry_run)


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
