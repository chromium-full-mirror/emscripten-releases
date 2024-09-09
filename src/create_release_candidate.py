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
from subprocess import check_call, check_output
import sys

script_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(script_dir)


def create_cl(source_rev, tag):
    if check_output(['git', 'status', '--porcelain'], cwd=root_dir).strip():
        print('tree is not clean')
        return 1

    # Create a new git branch
    branch_name = f'version_{tag}_rc'
    check_call(['git', 'checkout', '-b', branch_name], cwd=root_dir)

    # Copy DEPS from source_rev to DEPS.tagged_release
    deps = check_output(['git', 'show', f'{source_rev}:DEPS'], cwd=root_dir)
    with open(os.path.join(root_dir, 'DEPS.tagged_release'), 'w') as f:
        f.write(deps)

    check_call(['git', 'add', '-u', 'DEPS.tagged_release'], cwd=root_dir)
    message = f'Version {tag} RC\n\nDEPS from revision {source_rev}'
    check_call(['git', 'commit', '-m', message], cwd=root_dir)
    check_call(['git', 'cl', 'upload'])


def main(argv):
    tag = argv[1]
    if len(argv) > 2:
        source_rev = argv[2]
    else:
        source_rev = check_output(['git', 'rev-parse', 'HEAD']).decode()
    create_cl(source_rev, tag)


if __name__ == '__main__':
    sys.exit(main(sys.argv))
