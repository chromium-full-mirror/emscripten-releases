# -*- coding: utf-8 -*-

#   Copyright 2016 WebAssembly Community Group participants
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

import json
import os
import sys

import buildbot
import proc
import work_dirs

force_host_clang = True
use_sysroot = True


def SetupToolchain():
    return [
        sys.executable,
        os.path.join(work_dirs.GetV8(), 'build', 'toolchain', 'win',
                     'setup_toolchain.py')
    ]


def VSToolchainPy():
    return [
        sys.executable,
        os.path.join(work_dirs.GetV8(), 'build', 'vs_toolchain.py')
    ]


def WinToolchainJson():
    return os.path.join(work_dirs.GetV8(), 'build', 'win_toolchain.json')


def GetPrebuiltClang(binary):
    return os.path.join(work_dirs.GetV8(), 'third_party', 'llvm-build',
                        'Release+Asserts', 'bin', binary)


def SyncPrebuiltClang(src_dir):
    """Update the prebuilt clang toolchain used by chromium bots"""
    tools_clang = os.path.join(src_dir, 'tools', 'clang')
    assert os.path.isdir(tools_clang)
    proc.check_call([os.path.join(tools_clang, 'scripts', 'update.py')])


def SyncWinToolchain():
    """Update the VS toolchain used by Chromium bots"""
    proc.check_call(VSToolchainPy() + ['update'])


def GetVSEnv(dir):
    """Return the configured VS build environment block as a python dict."""
    # The format is a list of nul-terminated strings of the form var=val
    # where 'var' is the environment variable name, and 'val' is its value
    env = os.environ.copy()
    with open(os.path.join(dir, 'environment.x64'), 'rb') as f:
        entries = f.read().decode().split('\0')
        for e in entries:
            if not e:
                continue
            var, val = e.split('=', 1)
            env[var] = val
            print('ENV: %s = %s' % (var, val))

    return env


def SetUpVSEnv(outdir):
    """Set up the VS build environment used by Chromium bots"""

    # Get the chromium-packaged toolchain directory info in a JSON file
    proc.check_call(VSToolchainPy() + ['get_toolchain_dir'])
    with open(WinToolchainJson()) as f:
        paths = json.load(f)

    # Write path information (usable by a non-chromium build) into an
    # environment block
    runtime_dirs = os.pathsep.join(paths['runtime_dirs'])
    proc.check_call(SetupToolchain() +
                    [paths['path'], paths['win_sdk'], runtime_dirs, 'win',
                     'x64', 'environment.x64'],
                    cwd=outdir)


    # Recent versions of CMake use lib.exe to create archives. We need LLVM's
    # lib to use LTO, but it's not included in Chrome's packaging. lld-link
    # can be used as lib.exe (via the /lib flag) but CMake can't be forced to
    # inject the extra flag into every invocation. So we create a wrapper script
    # to replace lib.exe and redirect to lld-link with the extra flag.
    lld = GetPrebuiltClang('lld-link.exe')
    batch = f'''
@echo off
{lld} /lib %*
'''
    with open(GetPrebuiltClang('lib.bat'), 'w') as f:
        f.write(batch)
    return GetVSEnv(outdir)


def UsingGoma():
    return 'GOMA_DIR' in os.environ


def UsingReclient():
    return 'USE_RECLIENT' in os.environ


def ReclientDir():
    return os.path.join(work_dirs.GetV8(), 'buildtools', 'reclient')


def RewrapperCfg(platform):
    return os.path.join(work_dirs.GetV8(),
                        'buildtools',
                        'reclient_cfgs',
                        'chromium-browser-clang',
                        f'rewrapper_{platform}.cfg')


def ReproxyCfg():
    return os.path.join(work_dirs.GetV8(),
                        'buildtools',
                        'reclient_cfgs',
                        'reproxy.cfg')


def ParseConfigLine(line):
    line = line.strip()
    if not len(line) or line.startswith('#'):
        return None

    parts = line.split('=', 1)
    parts[0].lstrip('-')
    return (parts[0], True if len(parts) == 1 else parts[1])


def GetConfigFlag(config_file, flag):
    with open(config_file) as f:
        for line in f.readlines():
            parsed = ParseConfigLine(line)
            if parsed and parsed[0] == flag:
                return parsed[1]
    return None


def SetReclientEnv(host_platform):
    exec_root = work_dirs.GetExecRoot()
    os.environ['RBE_exec_root'] = exec_root
    # Reclient's canonicalize working_dir feature doesn't work with CMake's absolute paths.
    os.environ['RBE_canonicalize_working_dir'] = 'False'
    os.environ['RBE_env_var_allowlist'] = 'INCLUDE,LIB,LIBPATH'

    rewrapper_cfg = RewrapperCfg(host_platform)
    if not os.path.exists(rewrapper_cfg):
        return

    rbe_platform = GetConfigFlag(rewrapper_cfg, 'platform')
    if not rbe_platform or 'InputRootAbsolutePath' in rbe_platform:
        return

    os.environ[
        'RBE_platform'] = f'{rbe_platform},InputRootAbsolutePath={exec_root}'


def StartReproxy(host_platform):
    # TODO: check that the config has been downloaded correctly (e.g. with the .gclient file) and
    # that the user is logged into GCE auth

    # is it bad to just do SetReclientEnv(host_platform) here and add server_address to that set of vars?
    server_address = GetConfigFlag(RewrapperCfg(host_platform), 'server_address')
    os.environ['RBE_server_address'] = server_address
    bootstrap_cmd = [
        os.path.join(ReclientDir(), 'bootstrap') ,
        '-re_proxy=' + os.path.join(ReclientDir(), 'reproxy'),
        '-cfg=' + ReproxyCfg(),
        '-server_address=' + server_address # this flag doesn't seem to work?
    ]
    if buildbot.IsBot():
        for k ,v in os.environ.items():
            print(f'{k} = {v}')
    proc.check_call(bootstrap_cmd)


def GomaDir():
    return os.environ['GOMA_DIR']


def CMakeLauncherFlags(host_platform):
    flags = []
    if UsingReclient():
        compiler_launcher = ';'.join([
            os.path.join(ReclientDir(), 'rewrapper'),
            f'-cfg={RewrapperCfg(host_platform)}'])
    elif UsingGoma():
        compiler_launcher = os.path.join(GomaDir(), 'gomacc')
    else:
        try:
            compiler_launcher = proc.Which('ccache')
        except:  # noqa
            return flags

    flags.extend([
        '-DCMAKE_%s_COMPILER_LAUNCHER=%s' % (c, compiler_launcher)
        for c in ['C', 'CXX']
    ])
    return flags


def NinjaJobs():
    if force_host_clang:
        if UsingGoma():
            return ['-j', '50']
        elif UsingReclient():
            return ['-j', '150']
    return []


def SetForceHostClang(force):
    global force_host_clang
    force_host_clang = force


def ShouldForceHostClang():
    return force_host_clang


def SetUseSysroot(use):
    global use_sysroot
    use_sysroot = use


def ShouldUseSysroot():
    return use_sysroot
