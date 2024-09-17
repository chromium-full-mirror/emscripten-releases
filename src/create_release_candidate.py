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

import os
import subprocess
import sys

script_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(script_dir)


def run(cmd, capture_output=False):
    try:
        return subprocess.run(cmd, cwd=root_dir, capture_output=capture_output,
                              text=True, check=True).stdout
    except subprocess.CalledProcessError as e:
        print('Command failed: ' + ' '.join(cmd))
        print(e.stdout)
        print(e.stderr)
        raise e


def create_cl(source_rev, tag):
    if run(['git', 'status', '--porcelain', '--untracked-files=no']):
        print('tree is not clean')
        return 1

    # Create a new git branch
    branch_name = f'version_{tag}_rc'
    run(['git', 'checkout', '-b', branch_name])

    # Copy DEPS from source_rev to DEPS.tagged_release
    deps = run(['git', 'show', f'{source_rev}:DEPS'], capture_output=True)
    with open(os.path.join(root_dir, 'DEPS.tagged-release'), 'w') as f:
        f.write(deps)

    run(['git', 'add', '-u', 'DEPS.tagged-release'])
    message = f'Version {tag} RC\n\nDEPS from revision {source_rev}\n'
    message += 'This CL was created by src/create_release_candidate.py'
    run(['git', 'commit', '-m', message])
    run(['git', 'cl', 'upload'])


def main(argv):
    if len(argv) < 2:
        print('First argument must be the emscripten version (e.g. 3.1.66)')
    tag = argv[1]
    if len(argv) > 2:
        source_rev = argv[2]
    else:
        source_rev = run(['git', 'rev-parse', 'HEAD']).strip()
    create_cl(source_rev, tag)


if __name__ == '__main__':
    sys.exit(main(sys.argv))
