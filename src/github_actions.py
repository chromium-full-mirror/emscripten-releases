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

"""Helper module for triggering GitHub Actions workflows."""

import google_crc32c
import requests
from google.api_core import exceptions
from google.cloud import secretmanager

MAX_ATTEMPTS = 3
SECRET_NAME = 'projects/956827487526/secrets/emscripten-releases-token/versions/latest'
EMSDK_REPO_OWNER = 'emscripten-core'


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


def trigger_github_workflow(repo, workflow, payload):
    token = get_github_token()
    url = f'https://api.github.com/repos/{repo}/actions/workflows/{workflow}/dispatches'

    headers = {
        'Authorization': f'Bearer {token}',
        'Accept': 'application/vnd.github.v3+json',
    }

    response = requests.post(url, json=payload, headers=headers)

    if response.status_code == 204:
        print(f'Workflow {workflow} in {repo} triggered successfully!')
        return True
    else:
        print(f'Failed to trigger workflow {workflow} in {repo}. '
              f'Status code: {response.status_code}')
        print(response.text)
        return False


def trigger_emsdk_workflow(lto, nonlto, version):
    payload = {
        'ref': 'main',
        'inputs': {
            'lto-sha': lto,
            'nonlto-sha': nonlto,
            'version': version,
        },
    }
    trigger_github_workflow(f'{EMSDK_REPO_OWNER}/emsdk', 'create-release.yml', payload)


def trigger_rebaseline_workflow():
    payload = {
        'ref': 'main',
    }
    trigger_github_workflow(f'{EMSDK_REPO_OWNER}/emscripten', 'rebaseline-tests.yml',
                            payload)
