#!/usr/bin/env python3

#   Copyright 2024 WebAssembly Community Group participants
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

"""Trigger the EMSDK release workflow on github when HEAD is an LTO release

After an LTO build has finished, check whether all associated builds
have been uploaded. If so, post an API call to GitHub to trigger the
create-release.yml workflow on EMSDK.

LTO builds are builds with touch DEPS.tagged-release and have the
corresponding non-LTO build in their commit message.
"""

import os
import re
import subprocess
import sys

import buildbot
import cloud
import git_util
import github_actions

RELEASE_DEPS_FILE = 'DEPS.tagged-release'

script_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(script_dir)


def get_version(deps_file):
    with open(deps_file, 'r') as f:
        content = f.read()
    match = re.search(r"^# VERSION: (.*)$", content, re.MULTILINE)
    if match:
        return match.group(1)
    return None


def check():
    deps_file = os.path.join(root_dir, RELEASE_DEPS_FILE)
    version = get_version(deps_file)
    assert version, f'Could not parse version from {deps_file}'
    print(f'Parsed version {version} from {RELEASE_DEPS_FILE}')
    return 0


def main(argv):
    if '--check' in argv or '--test' in argv:
        return check()

    deps_file = os.path.join(root_dir, RELEASE_DEPS_FILE)
    if not git_util.RevisionModifiesFile(deps_file):
        print(f'HEAD revision does not modify {deps_file}')
        return 0
    if not buildbot.IsUploadingBot():
        print('Not an uploading bot.')
        return 0

    lto_sha = subprocess.check_output(['git', 'rev-parse', 'HEAD'],
                                      cwd=root_dir, text=True).strip()

    message_body = subprocess.check_output(
        ['git', 'log', '-1', '--pretty=%b', lto_sha], cwd=root_dir, text=True)

    match = re.search('DEPS from revision (.*)', message_body)
    if not match:
        print('non-LTO DEPS revision not found in commit message')
        # TODO: exit with error instead?
        # Would make sense if this runs as a test rather than build step
        return 0
    nonlto_sha = match.group(1)

    builds = cloud.ListBuilds(lto_sha)
    print('Already-uploaded builds:')
    print(builds)
    # We expect 2 builds each for Linux and Mac, and one for Windows
    builds_done = len(builds)
    if builds_done >= 5:
        print('All builds found, triggering release workflow.')
        version = get_version(deps_file)
        assert version, f'Could not parse version from {deps_file}'
        print(f'Found version {version} in {deps_file}')
        github_actions.trigger_emsdk_workflow(lto_sha, nonlto_sha, version)
    else:
        print(f'{builds_done} of 5 builds found, not triggering release workflow.')


if __name__ == '__main__':
    sys.exit(main(sys.argv))
