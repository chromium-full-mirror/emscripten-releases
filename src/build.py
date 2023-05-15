#!/usr/bin/env python3
# -*- coding: utf-8 -*-

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
import glob
import json
import multiprocessing
import platform
import os
import shutil
import struct
import sys
import tarfile
import tempfile
import textwrap
import time
import traceback
import zipfile

import buildbot
import cloud
from file_util import Chdir, Mkdir, Remove
import host_toolchains
import proc
import testing
import work_dirs
from urllib.request import urlopen, URLError

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(SCRIPT_DIR)
NINJA_DIR = os.path.join(ROOT_DIR, 'third_party', 'ninja')
JSVU_OUT_DIR = os.path.expanduser(os.path.join('~', '.jsvu'))
# Python executable that will be used by emscripten subprocesses.
# For now we just use the running executable, but in the future we could use
# a different one (for the python binary in emsdk).
EMSDK_PYTHON = sys.executable

EMSCRIPTEN_CONFIG_UPSTREAM = 'emscripten_config_upstream'
RELEASE_DEPS_FILE = 'DEPS.tagged-release'

WASM_STORAGE_BASE = 'https://wasm.storage.googleapis.com/'
CLANG_GIT_REPO = 'https://github.com/llvm/llvm-project'

# Update this number each time you want to create a clobber build.  If the
# clobber_version.txt file in the build dir doesn't match we remove ALL work
# dirs.  This works like a simpler version of chromium's landmine feature.
CLOBBER_BUILD_TAG = 43

V8_BUILD_SUBDIR = os.path.join('out.gn', 'x64.release')

LINUX_SYSROOT = 'sysroot_debian_stretch_amd64'
LINUX_SYSROOT_URL = WASM_STORAGE_BASE + LINUX_SYSROOT + '_v2.tar.xz'

options = None


def GetBuildDir(*args):
    return os.path.join(work_dirs.GetBuild(), *args)


def GetPrebuilt(*args):
    return os.path.join(work_dirs.GetPrebuilt(), *args)


def GetSrcDir(*args):
    return os.path.join(work_dirs.GetSync(), *args)


def GetInstallDir(*args):
    return os.path.join(work_dirs.GetInstall(), *args)


def GetTestDir(*args):
    return os.path.join(work_dirs.GetTest(), *args)


def GetLLVMSrcDir(*args):
    return GetSrcDir('llvm-project', *args)


def IsWindows():
    return sys.platform == 'win32'


def IsLinux():
    return sys.platform.startswith('linux')


def IsArm64():
    return platform.machine() in ('aarch64', 'arm64')


def IsMac():
    return sys.platform == 'darwin'


def Executable(name, extension='.exe'):
    return name + extension if IsWindows() else name


def WindowsFSEscape(path):
    return os.path.normpath(path).replace('\\', '/')


# Use prebuilt Node.js because the buildbots don't have node preinstalled
# Keep in sync with node version used in emsdk.
NODE_VERSION = '15.14.0'
NODE_BASE_NAME = 'node-v' + NODE_VERSION + '-'


def NodePlatformName():
    if IsMac():
        return 'darwin-x64'
    elif IsWindows():
        return 'win-x64'
    elif IsLinux():
        if IsArm64():
            return 'linux-arm64'
        else:
            return 'linux-x64'


def NodeBinDir():
    node_subdir = NODE_BASE_NAME + NodePlatformName()
    return GetPrebuilt(node_subdir, 'bin')


def NodeBin():
    return Executable(os.path.join(NodeBinDir(), 'node'))


def CMakePlatformName():
    return {
        'linux': 'linux',
        'linux2': 'linux',
        'darwin': 'macos',
        'win32': 'windows'
    }[sys.platform]


def CMakeArch():
    if IsMac():
        return 'universal'
    elif IsLinux() and IsArm64():
        return 'aarch64'
    else:
        return 'x86_64'


PREBUILT_CMAKE_VERSION = '3.21.3'
PREBUILT_CMAKE_BASE_NAME = 'cmake-%s-%s-%s' % (
    PREBUILT_CMAKE_VERSION, CMakePlatformName(), CMakeArch())


def PrebuiltCMakeDir(*args):
    return GetPrebuilt(PREBUILT_CMAKE_BASE_NAME, *args)


def PrebuiltCMakeBin():
    if IsMac():
        bin_dir = os.path.join('CMake.app', 'Contents', 'bin')
    else:
        bin_dir = 'bin'
    return PrebuiltCMakeDir(bin_dir, 'cmake')


def BuilderPlatformName():
    return {
        'linux': 'linux',
        'linux2': 'linux',
        'darwin': 'mac',
        'win32': 'windows'
    }[sys.platform]


# Known failures.
RUN_LLVM_TESTSUITE_FAILURES = [
    os.path.join(SCRIPT_DIR, 'test', 'llvmtest_known_failures.txt')
]

# Optimization levels
BARE_TEST_OPT_FLAGS = ['O0', 'O2']
EMSCRIPTEN_TEST_OPT_FLAGS = ['O0', 'O3']

NPROC = multiprocessing.cpu_count()

if IsMac():
    # Experimental temp fix for crbug.com/829034 stdout write sometimes fails
    from fcntl import fcntl, F_GETFL, F_SETFL
    fd = sys.stdout.fileno()
    flags = fcntl(fd, F_GETFL)
    fcntl(fd, F_SETFL, flags & ~os.O_NONBLOCK)

g_should_use_lto = None


def ShouldUseLTO():
    if options.use_lto == 'auto':
        # Avoid shelling out to git (via RevisionModifiesFile) more than once.
        global g_should_use_lto
        if g_should_use_lto is None:
            g_should_use_lto = RevisionModifiesFile(
                GetSrcDir(RELEASE_DEPS_FILE))
        return g_should_use_lto
    return options.use_lto == 'true'


def CopyBinaryToArchive(binary, prefix=''):
    """All binaries are archived in the same tar file."""
    install_bin = GetInstallDir(prefix, 'bin')
    print('Copying binary %s to archive %s' % (binary, install_bin))
    Mkdir(install_bin)
    shutil.copy2(binary, install_bin)


def CopyLibraryToArchive(library, prefix=''):
    """All libraries are archived in the same tar file."""
    install_lib = GetInstallDir(prefix, 'lib')
    print('Copying library %s to archive %s' % (library, install_lib))
    Mkdir(install_lib)
    shutil.copy2(library, install_lib)


def CopyLibraryToSysroot(library):
    """All libraries are archived in the same tar file."""
    install_lib = GetInstallDir('sysroot', 'lib', 'wasm32-wasi')
    print('Copying library %s to archive %s' % (library, install_lib))
    Mkdir(install_lib)
    shutil.copy2(library, install_lib)


def Archive(directory, print_content=False):
    """Create an archive file from directory."""
    # Use the format "native" to the platform
    if IsWindows():
        archive = Zip(directory, print_content)
    else:
        archive = Tar(directory, print_content)
    print('Archive created: %s [%s]' % (archive, os.path.getsize(archive)))
    return archive


def Tar(directory, print_content=False):
    assert os.path.isdir(directory), 'Must tar a directory to avoid tarbombs'
    up_directory, basename = os.path.split(directory)
    tar = os.path.join(up_directory, basename + '.tbz2')
    Remove(tar)
    if print_content:
        proc.check_call(
            ['find', basename, '-type', 'f', '-exec', 'ls', '-lhS', '{}', '+'],
            cwd=up_directory)
    proc.check_call(['tar', 'cjf', tar, basename], cwd=up_directory)
    proc.check_call(['ls', '-lh', tar], cwd=up_directory)
    return tar


def Zip(directory, print_content=False):
    assert os.path.isdir(directory), 'Must be a directory'
    dirname, basename = os.path.split(directory)
    archive = os.path.join(dirname, basename + '.zip')
    print('Creating zip archive', archive)
    with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as z:
        for root, dirs, files in os.walk(directory):
            for name in files:
                fs_path = os.path.join(root, name)
                zip_path = os.path.relpath(fs_path, os.path.dirname(directory))
                if print_content:
                    print('Adding', fs_path)
                z.write(fs_path, zip_path)
    print('Size:', os.stat(archive).st_size)
    return archive


def UploadFile(local_name, remote_name):
    """Archive the file with the given name, and with the LLVM git hash."""
    if not buildbot.IsUploadingBot():
        return
    buildbot.Link(
        'download',
        cloud.Upload(
            local_name, '%s/%s/%s' %
            (buildbot.BuilderName(), buildbot.BuildNumber(), remote_name)))


def UploadArchive(name, archive):
    """Archive the tar/zip file with the given name and the build number."""
    if not buildbot.IsUploadingBot():
        return
    extension = os.path.splitext(archive)[1]
    UploadFile(archive, 'wasm-%s%s' % (name, extension))


def FilterTargets(to_run, all_targets):
    for r in to_run:
        found = False
        for t in all_targets:
            if t.name == r:
                found = True
                yield t
        if not found:
            pretty_targets = TextWrapNameList(prefix='', items=all_targets)
            raise Exception(f'{r} not found in target list:\n{pretty_targets}')


class Source(object):
    """Metadata about a sync-able source repo on the waterfall"""
    def __init__(self, name, src_dir,
                 custom_sync=None):
        self.name = name
        self.src_dir = src_dir
        self.custom_sync = custom_sync

    def Sync(self):
        assert self.custom_sync
        self.custom_sync(self.name, self.src_dir)


def RevisionModifiesFile(f):
    """Return True if the file f is modified in the index, working tree, or
    HEAD commit."""
    if not os.path.isfile(f):
        return False
    cwd = os.path.dirname(f)
    # If the file is modified in the index or working tree, then return true.
    # This happens on trybots.
    status = proc.check_output(['git', 'status', '--porcelain', f],
                               cwd=cwd).strip()
    changed = len(status) != 0
    s = status if changed else '(unchanged)'
    print('%s git status: %s' % (f, s))
    if changed:
        return True
    # Else find the most recent commit that modified f, and return true if
    # that's the HEAD commit.
    head_rev = proc.check_output(['git', 'rev-parse', 'HEAD'], cwd=cwd).strip()
    last_rev = proc.check_output(
        ['git', 'rev-list', '-n1', 'HEAD', f], cwd=cwd).strip()
    print('Last rev modifying %s is %s, HEAD is %s' % (f, last_rev, head_rev))
    return head_rev == last_rev


def SyncToolchain(name, src_dir):
    if IsWindows():
        host_toolchains.SyncWinToolchain()
    else:
        host_toolchains.SyncPrebuiltClang(src_dir)
        cc = host_toolchains.GetPrebuiltClang('clang')
        cxx = host_toolchains.GetPrebuiltClang('clang++')
        assert os.path.isfile(cc), 'Expect clang at %s' % cc
        assert os.path.isfile(cxx), 'Expect clang++ at %s' % cxx


def SyncArchive(out_dir, name, url, create_out_dir=False):
    """Download and extract an archive (zip, tar.gz or tar.xz) file from a URL.

    The extraction happens in the prebuilt dir. If create_out_dir is True,
    out_dir will be created and the archive will be extracted inside. Otherwise
    the archive is expected to contain a top-level directory with all the
    files; this is expected to be 'out_dir', so if 'out_dir' already exists
    then the download will be skipped.
    """
    stamp_file = os.path.join(out_dir, 'stamp.txt')
    if os.path.isdir(out_dir):
        if os.path.isfile(stamp_file):
            with open(stamp_file) as f:
                stamp_url = f.read().strip()
            if stamp_url == url:
                print('%s directory already exists' % name)
                return
        print('%s directory exists but is not up-to-date' % name)
    print('Downloading %s from %s' % (name, url))

    if create_out_dir:
        os.makedirs(out_dir)
        work_dir = out_dir
    else:
        work_dir = os.path.dirname(out_dir)

    try:
        f = urlopen(url)
        print('URL: %s' % f.geturl())
        print('Info: %s' % f.info())
        with tempfile.NamedTemporaryFile() as t:
            t.write(f.read())
            t.flush()
            t.seek(0)
            print('Extracting into %s' % work_dir)
            ext = os.path.splitext(url)[-1]
            if ext == '.zip':
                with zipfile.ZipFile(t, 'r') as zip:
                    zip.extractall(path=work_dir)
            elif ext == '.xz':
                proc.check_call(['tar', '-xf', t.name], cwd=work_dir)
            else:
                tarfile.open(fileobj=t).extractall(path=work_dir)
    except URLError as e:
        print('Error downloading %s: %s' % (url, e))
        raise

    with open(stamp_file, 'w') as f:
        f.write(url + '\n')


def SyncPrebuiltCMake(name, src_dir):
    extension = '.zip' if IsWindows() else '.tar.gz'
    url = WASM_STORAGE_BASE + PREBUILT_CMAKE_BASE_NAME + extension
    SyncArchive(PrebuiltCMakeDir(), 'cmake', url)


def SyncPrebuiltNodeJS(name, src_dir):
    extension = {
        'darwin': 'tar.gz',
        'linux': 'tar.xz',
        'win32': 'zip'
    }[sys.platform]
    out_dir = GetPrebuilt(NODE_BASE_NAME + NodePlatformName())
    tarball = NODE_BASE_NAME + NodePlatformName() + '.' + extension
    node_url = WASM_STORAGE_BASE + tarball
    return SyncArchive(out_dir, name, node_url)


def SyncLinuxSysroot(name, src_dir):
    if not (IsLinux() and host_toolchains.ShouldUseSysroot()):
        return
    SyncArchive(GetPrebuilt(LINUX_SYSROOT),
                name,
                LINUX_SYSROOT_URL,
                create_out_dir=True)


def SyncReleaseDeps(name, src_dir):
    if not ShouldUseLTO():
        print('ShouldUseLTO is false, skipping release DEPS')
        return
    shutil.copy2(GetSrcDir(RELEASE_DEPS_FILE), GetSrcDir('DEPS'))
    proc.check_call(['gclient', 'sync'], cwd=GetSrcDir())


def NoSync(*args):
    pass


def AllSources():
    return [
        Source('host-toolchain', work_dirs.GetV8(),
               custom_sync=SyncToolchain),
        Source('cmake', '', # The source arg is ignored.
               custom_sync=SyncPrebuiltCMake),
        Source('nodejs', '',  # The source arg is ignored.
               custom_sync=SyncPrebuiltNodeJS),
        Source('sysroot', '', # The source arg is ignored.
               custom_sync=SyncLinuxSysroot),
        Source('deps', '', custom_sync=SyncReleaseDeps)
    ]


def RemoveIfBot(work_dir):
    if buildbot.IsBot():
        Remove(work_dir)


def Clobber():
    # Don't automatically clobber non-bot (local) work directories
    if not buildbot.IsBot() and not options.clobber:
        return

    clobber = options.clobber or buildbot.ShouldClobber()
    clobber_file = GetBuildDir('clobber_version.txt')
    if not clobber:
        if not os.path.exists(clobber_file):
            print('Clobber file %s does not exist.' % clobber_file)
            clobber = True
        else:
            existing_tag = int(open(clobber_file).read().strip())
            if existing_tag != CLOBBER_BUILD_TAG:
                print('Clobber file %s has tag %s.' %
                      (clobber_file, existing_tag))
                clobber = True

    if not clobber:
        return

    buildbot.Step('Clobbering work dir')
    if buildbot.IsEmscriptenReleasesBot() or not buildbot.IsBot():
        # Never clear source dirs locally.
        # On emscripten-releases, depot_tools and the recipe clear the rest.
        dirs = [work_dirs.GetBuild()]
    else:
        dirs = work_dirs.GetAll()
    for work_dir in dirs:
        RemoveIfBot(work_dir)
        Mkdir(work_dir)
    # Also clobber v8
    v8_dir = os.path.join(work_dirs.GetV8(), V8_BUILD_SUBDIR)
    Remove(v8_dir)
    with open(clobber_file, 'w') as f:
        f.write('%s\n' % CLOBBER_BUILD_TAG)


def SyncRepos(sync_targets):
    if not sync_targets:
        return
    buildbot.Step('Sync Repos')
    for repo in FilterTargets(sync_targets, AllSources()):
        repo.Sync()


# Build rules

def MaybeOverrideCMakeCompiler():
    if not host_toolchains.ShouldForceHostClang():
        if IsLinux() and IsArm64():
            return [
                '-DCMAKE_C_COMPILER=clang',
                '-DCMAKE_CXX_COMPILER=clang++'
            ]
        else:
            return []
    cc = 'clang-cl' if IsWindows() else 'clang'
    cxx = 'clang-cl' if IsWindows() else 'clang++'
    tools = [
        '-DCMAKE_C_COMPILER=' + Executable(
            host_toolchains.GetPrebuiltClang(cc)),
        '-DCMAKE_CXX_COMPILER=' + Executable(
            host_toolchains.GetPrebuiltClang(cxx)),
    ]
    # We need to use tools that work with LTO (i.e. they understand bitcode
    # when linking and creating archives).
    if IsWindows():
        tools.append('-DCMAKE_LINKER=' +
                     Executable(host_toolchains.GetPrebuiltClang('lld-link')))
        tools.append('-DCMAKE_AR=' +
                     host_toolchains.GetPrebuiltClang('lib.bat'))
    elif IsMac():
        tools.append('-DCMAKE_AR=' +
                     host_toolchains.GetPrebuiltClang('llvm-ar'))
        tools.append('-DCMAKE_RANLIB=' +
                     host_toolchains.GetPrebuiltClang('llvm-ranlib'))
        # LLVM's CMake wants to use libtool isntead of llvm-ar, but the Chrome
        # clang package doesn't have libtool. If we set CMAKE_LIBTOOL empty, it
        # will fall back to the default.
        tools.append('-DCMAKE_LIBTOOL=')
    return tools


def CMakeCommandBase():
    command = [PrebuiltCMakeBin(), '-G', 'Ninja']
    # Python's location could change, so always update CMake's cache
    command.extend(['-DPython3_EXECUTABLE=' + sys.executable,
                    '-DCMAKE_EXPORT_COMPILE_COMMANDS=ON',
                    '-DCMAKE_BUILD_TYPE=Release'])
    if IsMac():
        # Target MacOS Mojave (10.14). Keep this in sync with emsdk.py
        command.append('-DCMAKE_OSX_DEPLOYMENT_TARGET=10.14')
    elif IsWindows():
        # CMake's usual logic fails to find LUCI's git on Windows
        git_exe = proc.Which('git')
        command.append('-DGIT_EXECUTABLE=%s' % git_exe)
    return command


def CMakeCommandNative(args, build_dir, mac_cross=False):
    command = CMakeCommandBase()
    command.append('-DCMAKE_INSTALL_PREFIX=%s' % GetInstallDir())
    if UseLocalLibCXX():
        inc = GetInstallDir('include', 'c++', 'v1')
        command.append(f'-DCMAKE_CXX_FLAGS=-stdlib++-isystem{inc}')
        lib = GetInstallDir('lib')
        command.append(f'-DCMAKE_EXE_LINKER_FLAGS=-L{lib} -stdlib=libc++')
        command.append(f'-DCMAKE_SHARED_LINKER_FLAGS=-L{lib} -stdlib=libc++')
        command.append(f'-DCMAKE_MODULE_LINKER_FLAGS=-L{lib} -stdlib=libc++')

    if host_toolchains.ShouldUseSysroot():
        if IsLinux():
            command.append('-DCMAKE_SYSROOT=%s' % GetPrebuilt(LINUX_SYSROOT))
        elif IsMac():
            # Get XCode SDK path.
            xcode_sdk_path = proc.check_output(['xcrun',
                                                '--show-sdk-path']).strip()
            # Create relpath symlink if it doesn't exist.
            # If it does exist, but points to a different location, update it.
            symlink_path = os.path.join(build_dir, 'xcode_sdk')
            if os.path.lexists(
                symlink_path) and os.readlink(symlink_path) != xcode_sdk_path:
                os.remove(symlink_path)
            if not os.path.exists(symlink_path):
                os.symlink(xcode_sdk_path, symlink_path)
            command.append(f'-DCMAKE_OSX_SYSROOT={symlink_path}')
            command.append(f'-DCMAKE_SYSROOT={symlink_path}')
        else:
            assert(False, 'sysroot not supported on windows')

    if mac_cross:
        command.append('-DCMAKE_OSX_ARCHITECTURES=arm64')

    command.extend(MaybeOverrideCMakeCompiler())

    if host_toolchains.ShouldForceHostClang():
        # Goma doesn't have the "default" SDK compilers in its cache, so only
        # use Goma when using our prebuilt Clang.
        command.extend(host_toolchains.CMakeLauncherFlags())
    command.extend(args)
    # On Windows, CMake chokes on paths containing backslashes that come from
    # the command line. Probably they just need to be escaped, but using '/'
    # instead is easier and works just as well.
    return [arg.replace('\\', '/') for arg in command]


def CopyLLVMTools(build_dir, prefix=''):
    # The following aren't useful for now, and take up space.
    # DLLs are in bin/ on Windows but in lib/ on posix.
    for unneeded_tool in ('clang-check', 'clang-cl', 'clang-cpp',
                          'clang-extdef-mapping', 'clang-format',
                          'clang-func-mapping', 'clang-import-test',
                          'clang-linker-wrapper', 'clang-offload-bundler',
                          'clang-offload-packager', 'clang-refactor',
                          'clang-rename', 'clang-repl', 'clang-scan-deps',
                          'diagtool', 'git-clang-format', 'hmaptool', 'ld.lld',
                          'ld64.lld', 'ld64.lld.darwinnew', 'ld64.lld.darwinold',
                          'lld-link', 'libclang.dll', 'llvm-cov', 'llvm-ml',
                          'llvm-lib', 'llvm-pdbutil', 'llvm-profdata',
                          'llvm-rc'):
        Remove(GetInstallDir(prefix, 'bin', Executable(unneeded_tool)))

    for lib in ['libclang.%s' for suffix in ('so.*', 'dylib')]:
        Remove(GetInstallDir(prefix, 'lib', lib))

    # The following are useful, LLVM_INSTALL_TOOLCHAIN_ONLY did away with them.
    extra_bins = map(Executable, [
        'llvm-dwarfdump', 'llvm-dwp', 'llvm-nm', 'llvm-objdump', 'llvm-readobj',
        'llvm-size',
    ])
    for p in [
            glob.glob(os.path.join(build_dir, 'bin', b)) for b in extra_bins
    ]:
        for e in p:
            CopyBinaryToArchive(os.path.join(build_dir, 'bin', e), prefix)


def BuildEnv(build_dir, bin_subdir=False,
             runtime='Release'):
    if IsMac():
        # We need a ranlib that understands bitcode, but llvm-ranlib is not
        # included in Chrome's packaging. But ranlib is just ar by another name
        ranlib = host_toolchains.GetPrebuiltClang('llvm-ranlib')
        if not os.path.exists(ranlib):
            os.symlink(host_toolchains.GetPrebuiltClang('llvm-ar'), ranlib)
        return None
    if not IsWindows():
        return None
    cc_env = host_toolchains.SetUpVSEnv(build_dir)
    # This value matches the version of cl.exe currently used by the bots, but
    # it needs to be made explicit in order to run on Goma
    # (crbug.com/1292405). This will need to be updated when LLVM or another of
    # our projects requires a newer MSVC version.
    # Flags need to be injected via the env (rather than on the CMake command
    # line) so they add to rather than overriding the default flags.
    cc_env['CXXFLAGS'] = cc_env['CFLAGS'] = '-fmsc-version=1929'
    bin_dir = build_dir if not bin_subdir else os.path.join(build_dir, 'bin')
    Mkdir(bin_dir)
    assert runtime in ['Release', 'Debug']
    return cc_env


def LLVM(build_dir, mac_cross=False):
    buildbot.Step('LLVM')
    Mkdir(build_dir)
    cc_env = BuildEnv(build_dir, bin_subdir=True)
    build_dylib = 'ON'
    if IsWindows() or ShouldUseLTO() or options.link_static:
        build_dylib = 'OFF'
    cmake_flags = [
        '-DLLVM_ENABLE_LIBXML2=OFF',
        '-DLLVM_INCLUDE_EXAMPLES=OFF',
        '-DLLVM_BUILD_LLVM_DYLIB=%s' % build_dylib,
        '-DLLVM_LINK_LLVM_DYLIB=%s' % build_dylib,
        '-DCMAKE_BUILD_WITH_INSTALL_RPATH=ON',
        '-DLLVM_ENABLE_BINDINGS=OFF',
        # Our mac bot's toolchain's ld64 is too old for trunk libLTO.
        '-DLLVM_TOOL_LTO_BUILD=OFF',
        '-DLLVM_INSTALL_TOOLCHAIN_ONLY=ON',
        '-DLLVM_TARGETS_TO_BUILD=host;WebAssembly',
        '-DLLVM_ENABLE_PROJECTS=lld;clang',
        # linking libtinfo dynamically causes problems on some linuxes,
        # https://github.com/emscripten-core/emsdk/issues/252
        '-DLLVM_ENABLE_TERMINFO=%d' % (not IsLinux()),
        '-DLLVM_USE_CRT_RELEASE=MT',
        '-DLLVM_USE_CRT_DEBUG=MTd',
        '-DCLANG_ENABLE_ARCMT=OFF',
        '-DCLANG_ENABLE_STATIC_ANALYZER=OFF',
        '-DCLANG_REPOSITORY_STRING=%s' % CLANG_GIT_REPO,
        '-DLLVM_ENABLE_LLD=ON',
    ]
    if UseStaticLibCXX():
        cmake_flags += ['-DLLVM_STATIC_LINK_CXX_STDLIB=ON']

    ninja_targets = ('all', 'install')

    if ShouldUseLTO():
        targets = ['clang', 'lld', 'llvm-ar', 'llvm-addr2line', 'llvm-cxxfilt',
                   'llvm-dwarfdump', 'llvm-dwp', 'llvm-nm',
                   'llvm-objcopy', 'llvm-objdump', 'llvm-ranlib',
                   'llvm-readobj', 'llvm-size', 'llvm-strings',
                   'llvm-strip', 'llvm-symbolizer', 'clang-resource-headers']
        ninja_targets = ('distribution', 'install-distribution')
        cmake_flags.extend(['-DLLVM_ENABLE_ASSERTIONS=OFF',
                            '-DLLVM_INCLUDE_TESTS=OFF',
                            '-DLLVM_TOOLCHAIN_TOOLS=' + ';'.join(targets),
                            '-DLLVM_DISTRIBUTION_COMPONENTS=' + ';'.join(targets),
                            '-DLLVM_ENABLE_LTO=Thin'])

    else:
        cmake_flags.extend(['-DLLVM_ENABLE_ASSERTIONS=ON'])

    if mac_cross:
        # Cross builds need a native version of the tablegen tools to
        # run on the build machine. These can be built in a separate
        # "stage 1" build, but since our bots always build the full
        # toolchain as native before they build the cross toolchain,
        # we can just use tablegen from its build dir.
        native_build_dir = os.path.join(work_dirs.GetBuild(), 'llvm-out')
        lt = os.path.join(native_build_dir, 'bin', 'llvm-tblgen')
        ct = os.path.join(native_build_dir, 'bin', 'clang-tblgen')
        cmake_flags.extend(['-DLLVM_TABLEGEN=' + lt, '-DCLANG_TABLEGEN=' + ct])

    cmake_cmd =  CMakeCommandNative(
        [GetLLVMSrcDir('llvm')] + cmake_flags,
        build_dir,
        mac_cross=mac_cross)

    proc.check_call(cmake_cmd, cwd=build_dir, env=cc_env)

    # Copy the libc++ library to the build dir so that tablegen will run
    for suffix in ('2.dylib', 'so.2'):
        dylib = GetInstallDir('lib', f'libc++.{suffix}')
        if os.path.isfile(dylib):
            shutil.copy(dylib, os.path.join(build_dir, 'lib'))

    jobs = host_toolchains.NinjaJobs()
    proc.check_call(['ninja', '-v', ninja_targets[0]] + jobs,
                    cwd=build_dir, env=cc_env)
    proc.check_call(['ninja', ninja_targets[1]] + jobs,
                    cwd=build_dir, env=cc_env)

    CopyLLVMTools(build_dir)
    install_bin = GetInstallDir('bin')
    for target in ('clang', 'clang++'):
        for link in 'wasm32-', 'wasm32-wasi-':
            link = os.path.join(install_bin, link + target)
            if not IsWindows():
                if not os.path.islink(Executable(link)):
                    os.symlink(Executable(target), Executable(link))
            else:
                # Windows has no symlinks (at least not from python). Also
                # clang won't work as a native compiler anyway, so just install
                # it as wasm32-wasi-clang
                shutil.copy2(Executable(os.path.join(install_bin, target)),
                             Executable(link))

    # LTO builds clobber their working directories after build to avoid
    # incremental build problems. But we saved native_build_dir for the cross
    # build, so clobber it now.
    if mac_cross and ShouldUseLTO():
        RemoveIfBot(native_build_dir)


def LLVMTestDepends():
    buildbot.Step('LLVM Test Dependencies')
    build_dir = os.path.join(work_dirs.GetBuild(), 'llvm-out')
    proc.check_call(['ninja', '-v', 'test-depends'] +
                    host_toolchains.NinjaJobs(),
                    cwd=build_dir,
                    env=BuildEnv(build_dir, bin_subdir=True))


def TestLLVMRegression():
    build_dir = os.path.join(work_dirs.GetBuild(), 'llvm-out')
    cc_env = BuildEnv(build_dir, bin_subdir=True)
    if not os.path.isdir(build_dir):
        print('LLVM Build dir %s does not exist' % build_dir)
        buildbot.Fail()
        return

    def RunWithUnixUtils(cmd, **kwargs):
        if IsWindows():
            return proc.check_call(['git', 'bash'] + cmd, **kwargs)
        else:
            return proc.check_call(cmd, **kwargs)

    try:
        buildbot.Step('LLVM regression tests')
        RunWithUnixUtils(['ninja', 'check-all'], cwd=build_dir, env=cc_env)
    except proc.CalledProcessError:
        buildbot.FailUnless(lambda: IsWindows())


def Jsvu():
    buildbot.Step('jsvu')
    jsvu_dir = os.path.join(work_dirs.GetBuild(), 'jsvu')
    Mkdir(jsvu_dir)

    if IsWindows():
        # jsvu OS identifiers:
        # https://github.com/GoogleChromeLabs/jsvu#supported-engines
        os_id = 'windows64'
        js_engines = 'chakra'
    elif IsMac():
        os_id = 'mac64'
        js_engines = 'javascriptcore,v8'
    else:
        os_id = 'linux64'
        js_engines = 'javascriptcore'

    try:
        # https://github.com/GoogleChromeLabs/jsvu#installation
        # ...except we install it locally instead of globally.
        proc.check_call(['npm', 'install', 'jsvu'], cwd=jsvu_dir)

        jsvu_bin = Executable(
            os.path.join(jsvu_dir, 'node_modules', 'jsvu', 'cli.js'))
        # https://github.com/GoogleChromeLabs/jsvu#integration-with-non-interactive-environments
        proc.check_call(
            [jsvu_bin,
             '--os=%s' % os_id,
             '--engines=%s' % js_engines])

        # $HOME/.jsvu/chakra is now available on Windows.
        # $HOME/.jsvu/javascriptcore is now available on Mac.

        # TODO: Install the JSC binary in the output package, and add the
        # version info to the repo info JSON file (currently in GetRepoInfo)
    except proc.CalledProcessError:
        buildbot.Warn()


def UseLocalLibCXX():
    # Use our own libc++ to get around the Linux sysroot's very old
    # libstdc++. Also use it on mac.
    return not IsWindows() and host_toolchains.ShouldUseSysroot()


def UseStaticLibCXX():
    return UseLocalLibCXX() and (ShouldUseLTO() or options.link_static)


def LibCXX(build_dir, mac_cross=False):
    buildbot.Step('libcxx')
    Mkdir(build_dir)

    # We include either the shared library or the static library. The shared
    # version is used for the non-release builds to save space. However as an
    # extra special weird case, the LLVM regression test version (which does not
    # use LTO) needs to use static linking but also needs to be PIC because of the
    # dynamic loading tests.
    cmake_on = { False: 'OFF', True: 'ON' }
    should_use_static = UseStaticLibCXX()

    BuildEnv(build_dir)
    cmd = CMakeCommandNative(
        [GetLLVMSrcDir('runtimes'),
         '-DLLVM_ENABLE_RUNTIMES=libcxx;libcxxabi',
         # ABI version 2 gives some libc++ improvements, but the real reason is
         # to avoid any possibility of accidentally depending on system libc++
         '-DLIBCXX_ABI_VERSION=2',
         '-DLIBCXX_HAS_ATOMIC_LIB=OFF',
         f'-DLIBCXX_ENABLE_SHARED={cmake_on[not should_use_static]}',
         '-DLIBCXX_ENABLE_EXPERIMENTAL_LIBRARY=OFF',
         '-DLIBCXXABI_ENABLE_SHARED=OFF',
         '-DLIBCXX_INCLUDE_TESTS=OFF',
         '-DLIBCXXABI_INCLUDE_TESTS=OFF',
         '-DLIBCXX_ENABLE_STATIC_ABI_LIBRARY=ON',
         f'-DLIBCXX_INSTALL_STATIC_LIBRARY={cmake_on[should_use_static]}',
         f'-DLIBCXXABI_INSTALL_STATIC_LIBRARY={cmake_on[should_use_static]}',
         f'-DCMAKE_POSITION_INDEPENDENT_CODE={cmake_on[not ShouldUseLTO()]}',
         ], build_dir, mac_cross=mac_cross)
    # Filter out the stdlib flags because we are bootstrapping stdlib
    cmd = [x for x in cmd if not 'stdlib' in x]
    if IsMac():
        cmd.append('-DLIBCXX_USE_COMPILER_RT=ON')
    proc.check_call(cmd, cwd=build_dir)
    proc.check_call(['ninja', '-v', 'cxx', 'cxxabi'] + host_toolchains.NinjaJobs(),
                    cwd=build_dir)
    proc.check_call(['ninja', 'install-cxx', 'install-cxxabi'], cwd=build_dir)


def Binaryen(build_dir, mac_cross=False):
    buildbot.Step('binaryen')
    Mkdir(build_dir)
    # Currently it's a bad idea to do a non-asserts build of Binaryen
    cc_env = BuildEnv(build_dir, bin_subdir=True, runtime='Debug')

    cmake_command = CMakeCommandNative(
        [GetSrcDir('binaryen')],build_dir, mac_cross=mac_cross)
    cmake_command.extend(['-DINSTALL_LIBS=OFF', '-DBUILD_TESTS=OFF'])
    if ShouldUseLTO():
        cmake_command.append('-DBUILD_STATIC_LIB=ON')
        cmake_command.append('-DBYN_ENABLE_LTO=ON')

    proc.check_call(cmake_command, cwd=build_dir, env=cc_env)
    proc.check_call(['ninja', '-v'] + host_toolchains.NinjaJobs(),
                    cwd=build_dir, env=cc_env)
    proc.check_call(['ninja', 'install'], cwd=build_dir, env=cc_env)


def InstallEmscripten():
    src_dir = GetSrcDir('emscripten')
    em_install_dir = GetInstallDir('emscripten')
    Remove(em_install_dir)
    print('Installing emscripten into %s' % em_install_dir)
    proc.check_call([os.path.join('tools', 'install.py'), em_install_dir],
                    cwd=src_dir)
    print('Running npm install ...')
    proc.check_call(['npm', 'ci', '--production', '--no-optional'], cwd=em_install_dir)
    # Manually install the appropriate native Closure Compiler package
    # if available.
    #
    # This is currently needed because npm ci will install the packages
    # for Closure for all platforms, adding 180MB to the download size
    # There are two problems here:
    #   1. npm ci does not consider the platform of optional dependencies
    #      https://github.com/npm/cli/issues/558
    #   2. A bug with the native compiler has bloated the packages from
    #      30MB to almost 300MB
    #      https://github.com/google/closure-compiler-npm/issues/186
    # If either of these bugs are fixed we could consider removing this
    # hack.
    native = None
    if IsMac():
        native = 'google-closure-compiler-osx'
    elif IsWindows():
        native = 'google-closure-compiler-windows'
    elif IsLinux() and platform.machine() == 'x86_64':
        native = 'google-closure-compiler-linux'
    if native:
        # Keep this in sync with package.json
        native += '@20220502.0.0'
        proc.check_call(['npm', 'install', '--production', '--no-optional', native],
                        cwd=em_install_dir)


def Emscripten():
    InstallEmscripten()

    def WriteEmscriptenConfig(infile, outfile):
        with open(infile) as config:
            text = config.read().replace('{{WASM_INSTALL}}',
                                         WindowsFSEscape(GetInstallDir()))
            text = text.replace('{{PREBUILT_NODE}}',
                                WindowsFSEscape(NodeBin()))
        with open(outfile, 'w') as config:
            config.write(text)

    # Set up the emscripten config and compile the libraries
    buildbot.Step('emscripten')
    config = GetInstallDir(EMSCRIPTEN_CONFIG_UPSTREAM)
    print('Config file: ', config)
    src_config = os.path.join(SCRIPT_DIR, os.path.basename(config))
    WriteEmscriptenConfig(src_config, config)

    env = os.environ.copy()
    env['EM_CONFIG'] = config
    env['EMSDK_PYTHON'] = EMSDK_PYTHON
    # Use emscripten's embuilder to prebuild the system libraries.
    # This depends on binaryen already being built and installed into the
    # archive/install dir.
    embuilder = Executable(GetInstallDir('emscripten', 'embuilder'), '.bat')
    proc.check_call([embuilder, 'build', 'SYSTEM'], env=env)

    # Remove the sanity file.  This means it will get generated on first
    # use without clearing the cache.
    sanity = GetInstallDir('emscripten', 'cache', 'sanity.txt')
    if os.path.exists(sanity):
        os.remove(sanity)


def VerifyEmscriptenCrossBuild():
    # Ensure that all binaries have the correct architecture. There is
    # currently one exception which is allowed to be x86_64:
    closure_binary = 'google-closure-compiler-osx/compiler'
    print('Verifying architecture of MacOS binaries')
    for root, dirs, files in os.walk(GetInstallDir()):
        for f in files:
            path = os.path.join(root, f)
            with open(path, 'rb') as fd:
                header = fd.read(8)
                if len(header) < 8:
                    continue
                is_macho = struct.unpack_from('I', header)[0] == 0xfeedfacf
                if not is_macho:
                    continue
                cpu_type = struct.unpack_from('I', header, 4)[0]
                is_x86_64 = cpu_type == 0x1000007
                is_arm64 = cpu_type == 0x100000c
                if is_arm64:
                    continue
                if not (path.endswith(closure_binary) and is_x86_64):
                    print(f'{path} is a non-arm64 binary:')
                    proc.check_call(['file', path])
                    raise Exception('Native binary in the cross build')


def ArchiveBinaries(mac_cross=False):
    buildbot.Step('Archive binaries')
    # Archive everything in the install directory.
    filename = 'binaries'
    if mac_cross:
        assert IsMac() and platform.machine() == 'x86_64'
        filename += '-arm64'
        VerifyEmscriptenCrossBuild()
    archive = Archive(GetInstallDir(), print_content=buildbot.IsBot())

    # Also make a local copy for running tests.
    if IsMac() and not mac_cross:
        copy = os.path.join(os.path.dirname(archive), 'test-install.tbz2')
        print(f'Copying {archive} to {copy}')
        shutil.copy(archive, copy)
    if not buildbot.IsUploadingBot():
        return
    UploadArchive(filename, archive)


def ExtractArchive():
    Remove(GetInstallDir())
    upper_dir = os.path.dirname(GetInstallDir())
    proc.check_call(['tar', '-xvjf',
        os.path.join(upper_dir, 'test-install.tbz2')],
        cwd=upper_dir)


def DebianPackage():
    if not (IsLinux() and buildbot.IsBot()):
        return

    buildbot.Step('Debian package')
    try:
        if buildbot.BuildNumber():
            message = ('Automatic build %s produced on http://wasm-stat.us' %
                       buildbot.BuildNumber())
            version = '0.1.' + buildbot.BuildNumber()
            proc.check_call(['dch', '-D', 'unstable', '-v', version, message],
                            cwd=ROOT_DIR)
        proc.check_call(['debuild', '--no-lintian', '-i', '-us', '-uc', '-b'],
                        cwd=ROOT_DIR)
        if buildbot.BuildNumber():
            proc.check_call(['git', 'checkout', 'debian/changelog'],
                            cwd=ROOT_DIR)

            debfile = os.path.join(os.path.dirname(ROOT_DIR),
                                   'wasm-toolchain_%s_amd64.deb' % version)
            UploadFile(debfile, os.path.basename(debfile))
    except proc.CalledProcessError:
        # Note the failure but allow the build to continue.
        buildbot.Fail()
        return


class Build(object):
    def __init__(self, name_, runnable_,
                 incremental_build_dir=None,
                 clobber_lto=True,
                 *args, **kwargs):
        self.name = name_
        self.runnable = runnable_
        self.incremental_build_dir = incremental_build_dir
        self.clobber_lto = clobber_lto
        self.args = args
        self.kwargs = kwargs

        if incremental_build_dir:
            self.kwargs['build_dir'] = incremental_build_dir

    def Run(self):
        # When using LTO we always want a clean build (the previous
        # build was non-LTO)
        if self.incremental_build_dir and ShouldUseLTO():
            RemoveIfBot(self.incremental_build_dir)
        try:
            self.runnable(*self.args, **self.kwargs)
        except Exception:
            # If the build fails (even non-LTO), a possible cause is a build
            # config change, so clobber the work dir for next time.
            if self.incremental_build_dir:
                RemoveIfBot(self.incremental_build_dir)
            raise
        finally:
            # When using LTO we want to always clean up afterward,
            # (the next build will be non-LTO).
            if self.incremental_build_dir and ShouldUseLTO() and self.clobber_lto:
                RemoveIfBot(self.incremental_build_dir)


def Summary():
    buildbot.Step('Summary')

    print('Failed steps: %s.' % buildbot.Failed())
    for step in buildbot.FailedList():
        print('    %s' % step)
    print('Warned steps: %s.' % buildbot.Warned())
    for step in buildbot.WarnedList():
        print('    %s' % step)

    if buildbot.Failed():
        buildbot.Fail()


# TODO: Now that we've gotten rid of the complex filtering mechanism, we can
# use a better data structure for this.
def AllBuilds():
    return [
        # Host tools
        Build('libcxx', LibCXX,
              incremental_build_dir=os.path.join(
                  work_dirs.GetBuild(),'libcxx-out')),
        Build('libcxx-cross', LibCXX,
              incremental_build_dir=os.path.join(
                  work_dirs.GetBuild(),'libcxx-cross-out'), mac_cross=True),
        Build('llvm', LLVM,
              incremental_build_dir=os.path.join(
                  work_dirs.GetBuild(), 'llvm-out'), clobber_lto=not IsMac()),
        Build('llvm-cross', LLVM,
              incremental_build_dir=os.path.join(
                  work_dirs.GetBuild(), 'llvm-cross-out'), mac_cross=True),
        Build('llvm-test-depends', LLVMTestDepends),
        Build('jsvu', Jsvu),
        Build('binaryen', Binaryen,
              incremental_build_dir=os.path.join(
                  work_dirs.GetBuild(), 'binaryen-out')),
        Build('binaryen-cross', Binaryen,
              incremental_build_dir=os.path.join(
                  work_dirs.GetBuild(), 'binaryen-cross-out'), mac_cross=True),
        Build('emscripten', Emscripten),
        # Archive
        Build('archive', ArchiveBinaries),
        Build('archive-cross', ArchiveBinaries, mac_cross=True),
        Build('extract-archive', ExtractArchive),
        Build('debian', DebianPackage),
    ]


def BuildRepos(builds):
    for b in FilterTargets(builds, AllBuilds()):
        b.Run()


class Test(object):
    def __init__(self, name_, runnable_):
        self.name = name_
        self.runnable = runnable_

    def Test(self):
        self.runnable()


def ExecuteEmscriptenTestSuite(name, tests, config, outdir, warn_only=False):
    buildbot.Step('Execute emscripten testsuite (%s)' % name)
    Mkdir(outdir)

    # Before we can run the tests we prepare the installed emscripten
    # directory by copying of some test data which is otherwise excluded by
    # emscripten install script (tools/install.py).
    # We also need to run npm to get the devDependencies needed by the
    # test suite.
    em_install_dir = GetInstallDir('emscripten')
    installed_tests = os.path.join(em_install_dir, 'test', 'third_party')
    if not os.path.exists(installed_tests):
        src_dir = GetSrcDir('emscripten', 'test', 'third_party')
        print('Copying directory %s to %s' % (src_dir, em_install_dir))
        shutil.copytree(src_dir, installed_tests, symlinks=True)

    # Ideally we would put this inside the above block/condition but there
    # is a bug on win32 that is currently causing 'test/third_party' to
    # be installed by install.py.
    print('Running npm install ...')
    proc.check_call(['npm', 'ci', '--no-optional'], cwd=em_install_dir)

    cmd = [
        Executable(GetInstallDir('emscripten', 'test', 'runner'), '.bat'),
        '--em-config', config
    ] + tests
    test_env = os.environ.copy()
    test_env['EMTEST_SKIP_V8'] = '1'
    # Our bots don't currently have a recent enough version of node installed
    # to run wasm64, wasm EH, or simd tests.
    test_env['EMTEST_SKIP_WASM64'] = '1'
    test_env['EMTEST_SKIP_SIMD'] = '1'
    test_env['EMTEST_SKIP_EH'] = '1'
    test_env['EMTEST_SKIP_SCONS'] = '1'
    test_env['EMSDK_PYTHON'] = EMSDK_PYTHON
    if buildbot.IsBot():
        if IsWindows():
            test_env['EMTEST_LACKS_NATIVE_CLANG'] = '1'
        if not IsLinux():
            test_env['EMTEST_SKIP_PKG_CONFIG'] = '1'
    try:
        proc.check_call(cmd, cwd=outdir, env=test_env)
    except proc.CalledProcessError:
        buildbot.FailUnless(lambda: warn_only)


def TestEmtest():
    tests = options.test_params if options.test_params else ['wasm2', 'other']
    ExecuteEmscriptenTestSuite('emwasm', tests,
                               GetInstallDir(EMSCRIPTEN_CONFIG_UPSTREAM),
                               os.path.join(work_dirs.GetTest(), 'emtest-out'))


def TestLLVMTestSuite():
    buildbot.Step('Execute LLVM TestSuite')

    outdir = GetBuildDir('llvmtest-out')
    # The compiler changes on every run, so incremental builds don't make
    # sense.
    Remove(outdir)
    Mkdir(outdir)
    # The C++ tests explicitly link libstdc++ for some reason, but we use
    # libc++ and it's unnecessary to link it anyway. So create an empty
    # libstdc++.a
    proc.check_call([GetInstallDir('bin', 'llvm-ar'), 'rc', 'libstdc++.a'],
                    cwd=outdir)
    # This has to be in the environment and not TEST_SUITE_EXTRA_C_FLAGS
    # because CMake doesn't append the flags to the try-compiles.
    os.environ['EM_CONFIG'] = GetInstallDir(EMSCRIPTEN_CONFIG_UPSTREAM)
    command = [GetInstallDir('emscripten', 'emcmake')] + CMakeCommandBase() + [
        GetSrcDir('llvm-test-suite'), '-DCMAKE_C_COMPILER=' +
        GetInstallDir('emscripten', 'emcc'), '-DCMAKE_CXX_COMPILER=' +
        GetInstallDir('emscripten', 'em++'), '-DTEST_SUITE_RUN_UNDER=' +
        NodeBin(), '-DTEST_SUITE_USER_MODE_EMULATION=ON',
        '-DTEST_SUITE_SUBDIRS=SingleSource;MicroBenchmarks',
        # The tests for the in-progress matrix extension don't currently work.
        '-DCOMPILER_HAS_MATRIX_FLAG=OFF',
        '-DTEST_SUITE_EXTRA_EXE_LINKER_FLAGS=' +
        '-L %s -sTOTAL_MEMORY=1024MB -sEXIT_RUNTIME ' % outdir +
        '-lnodefs.js -sNODERAWFS -sSTACK_SIZE=128KB',
        '-DTEST_SUITE_LLVM_SIZE=' + GetInstallDir('emscripten', 'emsize.py')
    ]

    proc.check_call(command, cwd=outdir)
    proc.check_call(['ninja', '-v'], cwd=outdir)
    results_file = 'results.json'
    lit = GetBuildDir('llvm-out', 'bin', 'llvm-lit')
    proc.call([lit, '-v', '-o', results_file, '.'], cwd=outdir)

    with open(os.path.join(outdir, results_file)) as results_fd:
        json_results = json.loads(results_fd.read())

    def get_names(code):
        # Strip the unneccessary spaces from the test name
        return [
            r['name'].replace('test-suite :: ', '')
            for r in json_results['tests'] if r['code'] == code
        ]

    failures = get_names('FAIL')
    successes = get_names('PASS')

    expected_failures = testing.parse_exclude_files(
        RUN_LLVM_TESTSUITE_FAILURES, [])
    unexpected_failures = [f for f in failures if f not in expected_failures]
    unexpected_successes = [f for f in successes if f in expected_failures]

    if len(unexpected_failures) > 0:
        print('Emscripten unexpected failures:')
        for test in unexpected_failures:
            print(test)
    if len(unexpected_successes) > 0:
        print('Emscripten unexpected successes:')
        for test in unexpected_successes:
            print(test)

    if len(unexpected_failures) + len(unexpected_successes) > 0:
        buildbot.Fail()


ALL_TESTS = [
    Test('llvm-regression', TestLLVMRegression),
    # These tests do have interesting differences on OSes (especially the
    # 'other' tests) and eventually should run everywhere.
    Test('emtest', TestEmtest),
    Test('llvmtest', TestLLVMTestSuite),
]


def TextWrapNameList(prefix, items):
    width = 80  # TODO(binji): better guess?
    names = sorted(item.name for item in items)
    return '%s%s' % (prefix,
                     textwrap.fill(' '.join(names),
                                   width,
                                   initial_indent='  ',
                                   subsequent_indent='  '))


def ParseArgs():
    def SplitComma(arg):
        if not arg:
            return None
        return arg.split(',')

    epilog = '\n\n'.join([
        TextWrapNameList('sync targets:\n', AllSources()),
        TextWrapNameList('build targets:\n', AllBuilds()),
        TextWrapNameList('test targets:\n', ALL_TESTS),
    ])

    parser = argparse.ArgumentParser(
        description='Wasm waterfall top-level CI script',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=epilog)

    parser.add_argument(
        '--sync-dir', dest='sync_dir', help='Directory for syncing sources')
    parser.add_argument(
        '--build-dir', dest='build_dir', help='Directory for build output')
    parser.add_argument(
        '--prebuilt-dir', dest='prebuilt_dir',
        help='Directory for prebuilt output')
    parser.add_argument(
        '--v8-dir', dest='v8_dir',
        help='Directory for V8 checkout/build')
    parser.add_argument(
        '--test-dir', dest='test_dir', help='Directory for test output')
    parser.add_argument(
        '--install-dir', dest='install_dir',
        help='Directory for installed output')

    parser.add_argument(
        '--sync-include', dest='sync_include', default='', type=SplitComma,
        help='Include only the comma-separated list of sync targets')

    parser.add_argument(
        '--build-include', dest='build_include', default='', type=SplitComma,
        help='Include only the comma-separated list of build targets')

    parser.add_argument(
        '--test-include', dest='test_include', default='', type=SplitComma,
        help='Include only the comma-separated list of test targets')

    parser.add_argument(
        '--test-params', dest='test_params', default='', type=SplitComma,
        help='Test selector to pass through to emscripten testsuite runner')

    parser.add_argument(
        '--no-threads', action='store_true',
        help='Disable use of thread pool to building and testing')
    parser.add_argument(
        '--no-host-clang', dest='host_clang', action='store_false',
        help="Don't force chrome clang as the host compiler")
    parser.add_argument(
        '--no-sysroot', dest='use_sysroot', action='store_false',
        help="Don't use the V8 sysroot to build on Linux")
    parser.add_argument(
        '--clobber', dest='clobber', default=False, action='store_true',
        help="Delete working directories, forcing a clean build")
    parser.add_argument(
        '--use-lto', dest='use_lto', default=False, action='store',
        choices=['true', 'false', 'auto'],
        help='Use extra optimization for host binaries')
    parser.add_argument(
        '--link-static', dest='link_static', default=False, action='store_true',
        help='Link LLVM statically instead of using the libLLVM dylib'
             ' (required to run the LLVM regression tests)')

    return parser.parse_args()


def AddToPath(path):
    print("adding to path: %s" % path)
    os.environ['PATH'] = path + os.pathsep + os.environ['PATH']


def run(sync_targets, build_targets, test_targets):
    Clobber()
    Chdir(SCRIPT_DIR)
    for work_dir in work_dirs.GetAll():
        Mkdir(work_dir)
    SyncRepos(sync_targets)

    # Add prebuilt cmake to PATH so any subprocesses use a consistent cmake.
    AddToPath(os.path.dirname(PrebuiltCMakeBin()))

    # Add ninja to the PATH (needed for both cmake and for running emscripten
    # tests).
    AddToPath(NINJA_DIR)

    # `npm` uses whatever `node` is in `PATH`. To make sure it uses the
    # Node.js version we want, we prepend the node bin dir to `PATH`.
    AddToPath(NodeBinDir())

    try:
        BuildRepos(build_targets)
    except Exception:
        # If any exception reaches here, do not attempt to run the tests; just
        # log the error for buildbot and exit
        print("Exception thrown in build step.")
        traceback.print_exc()
        buildbot.Fail()
        Summary()
        return 1

    for t in FilterTargets(test_targets, ALL_TESTS):
        t.Test()

    # Keep the summary step last: it'll be marked as red if the return code is
    # non-zero. Individual steps are marked as red with buildbot.Fail().
    Summary()
    return buildbot.Failed()


def main():
    global options
    start = time.time()
    options = ParseArgs()
    print('Python version %s' % sys.version)
    print('sys.executable = %s' % sys.executable)
    print('EMSDK_PYTHON = %s' % EMSDK_PYTHON)

    if options.no_threads:
        testing.single_threaded = True

    if options.sync_dir:
        work_dirs.SetSync(options.sync_dir)
    if options.build_dir:
        work_dirs.SetBuild(options.build_dir)
    if options.v8_dir:
        work_dirs.SetV8(options.v8_dir)
    if options.test_dir:
        work_dirs.SetTest(options.test_dir)
    if options.install_dir:
        work_dirs.SetInstall(options.install_dir)
    if options.prebuilt_dir:
        work_dirs.SetPrebuilt(options.prebuilt_dir)
    if not options.host_clang:
        host_toolchains.SetForceHostClang(False)
    if not options.use_sysroot:
        host_toolchains.SetUseSysroot(False)

    sync_include = options.sync_include if options.sync_include else []
    build_include = options.build_include if options.build_include else []
    test_include = options.test_include if options.test_include else []


    try:
        ret = run(sync_include, build_include, test_include)
        print('Completed in {}s'.format(time.time() - start))
        return ret
    except:  # noqa
        traceback.print_exc()
        # If an except is raised during one of the steps we still need to
        # print the @@@STEP_FAILURE@@@ annotation otherwise the annotator
        # makes the failed stap as green:
        # TODO(sbc): Remove this if the annotator is fixed:
        # http://crbug.com/647357
        if buildbot.current_step:
            buildbot.Fail()
        return 1


if __name__ == '__main__':
    sys.exit(main())
