#!/usr/bin/env python3
# -*- coding: utf-8 -*-

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

import argparse
import os
import subprocess
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(SCRIPT_DIR)

import host_toolchains


def main():
    parser = argparse.ArgumentParser(
        description='Reclient wrapper for compiler execution and reproxy management.',
        usage='%(prog)s [options] | <compiler> [compiler_args...]')
    parser.add_argument('--start-reproxy', action='store_true',
                        help='Start the reproxy process')
    parser.add_argument('--stop-reproxy', action='store_true',
                        help='Stop the reproxy process')
    parser.add_argument('--status-reproxy', action='store_true',
                        help='Check the status of the reproxy process')

    args, compiler_cmd = parser.parse_known_args()

    # If no arguments are passed, show help
    if not (args.start_reproxy or args.stop_reproxy or args.status_reproxy) and not compiler_cmd:
        parser.print_help()
        return 1

    host_platform = host_toolchains.GetHostPlatform()

    if args.status_reproxy:
        server_address = host_toolchains.GetReproxyServerAddress(host_platform)
        if not server_address:
            print('Could not determine server address from environment or config.')
            return 1

        if host_toolchains.IsReproxyRunning(server_address):
            print(f'Reproxy is RUNNING (at {server_address})')
            return 0
        else:
            print(f'Reproxy is STOPPED (at {server_address})')
            return 1

    if args.start_reproxy:
        host_toolchains.StartReproxy(host_platform)
        return 0

    if args.stop_reproxy:
        return host_toolchains.StopReproxy(host_platform)

    # Set up environment variables
    host_toolchains.SetReclientEnv(host_platform)

    rewrapper = os.path.join(host_toolchains.ReclientDir(), 'rewrapper')
    rewrapper_cfg = host_toolchains.RewrapperCfg(host_platform)

    # The arguments passed to this script are the compiler and its arguments
    cmd = [rewrapper, f'-cfg={rewrapper_cfg}'] + compiler_cmd

    os.execv(rewrapper, cmd)


if __name__ == '__main__':
    sys.exit(main())
