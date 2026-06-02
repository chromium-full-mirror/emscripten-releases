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

import google_crc32c
import requests
from google.api_core import exceptions
from google.cloud import secretmanager

import build
import buildbot
import cloud

MAX_ATTEMPTS = 3
SECRET_NAME = 'projects/956827487526/secrets/emscripten-releases-token/versions/latest'
# To test this script locally or on a trybot, modify this and lto_sha below
EMSDK_REPO_OWNER = 'emscripten-core'

script_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(script_dir)


def get_github_token():
    client = secretmanager.SecretManagerServiceClient()
    retry = 0
    response = None
    while retry < MAX_ATTEMPTS:
        try:
            # Access the latest secret version.
            response = client.access_secret_version(
                request={'name': SECRET_NAME}, timeout=30.0)
            crc32c = google_crc32c.Checksum()
            crc32c.update(response.payload.data)
            if response.payload.data_crc32c != int(crc32c.hexdigest(), 16):
                raise Exception(f'Secret checksum fail {response.payload.data_crc32c}')
            return response.payload.data.decode('UTF-8')
        except exceptions.RetryError:
            retry += 1
            print(f'Fetching OTA from Secret Manager has timed out. Retrying {retry}')
    # If we come here, we have hit the retry limit. Fail this run.
    raise Exception('Failed to fetch the OTA password.')


def get_version(deps_file):
    with open(deps_file, 'r') as f:
        content = f.read()
    match = re.search(r"^# VERSION: (.*)$", content, re.MULTILINE)
    if match:
        return match.group(1)
    return None


def trigger_emsdk_workflow(lto, nonlto, version):
    token = get_github_token()
    url = f'https://api.github.com/repos/{EMSDK_REPO_OWNER}/emsdk/actions/workflows/create-release.yml/dispatches'

    payload = {
        'ref': 'main',
        'inputs': {
            'lto-sha': lto,
            'nonlto-sha': nonlto,
            'version': version,
        }
    }

    headers = {
        'Authorization': f'Bearer {token}',
        'Accept': 'application/vnd.github.v3+json'
    }

    response = requests.post(url, json=payload, headers=headers)

    if response.status_code == 204:
        print('Workflow dispatch event triggered successfully!')
    else:
        print('Failed to trigger workflow dispatch event.'
              f'Status code: {response.status_code}')
        print(response.text)


def main(argv):
    deps_file = os.path.join(root_dir, build.RELEASE_DEPS_FILE)
    if not build.RevisionModifiesFile(deps_file):
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
        trigger_emsdk_workflow(lto_sha, nonlto_sha, version)
    else:
        print(f'{builds_done} of 5 builds found, not triggering release workflow.')


if __name__ == '__main__':
    sys.exit(main(sys.argv))
