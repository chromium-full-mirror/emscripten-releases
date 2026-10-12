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

import argparse
import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(SCRIPT_DIR)

import host_toolchains  # noqa: E402


def main():
    parser = argparse.ArgumentParser(
        description='Manage the reclient reproxy process.')
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--start', '--start-reproxy', dest='start_reproxy',
                       action='store_true',
                       help='Start the reproxy process (default)')
    group.add_argument('--stop', '--stop-reproxy', dest='stop_reproxy',
                       action='store_true',
                       help='Stop the reproxy process')
    group.add_argument('--status', '--status-reproxy', dest='status_reproxy',
                       action='store_true',
                       help='Check the status of the reproxy process')

    args = parser.parse_args()
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

    if args.stop_reproxy:
        return host_toolchains.StopReproxy(host_platform)

    host_toolchains.StartReproxy(host_platform)
    return 0


if __name__ == '__main__':
    sys.exit(main())
