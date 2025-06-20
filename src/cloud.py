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

import proc
import buildbot

CLOUD_STORAGE_BASE_URL = 'https://storage.googleapis.com/'
EMSCRIPTEN_RELEASES_CLOUD_STORAGE_PATH = \
    'webassembly/emscripten-releases-builds/'
SKIA_PERF_STORAGE_PATH = 'emscripten-perf-public/ingest/'


def GetCloudStoragePath():
    return EMSCRIPTEN_RELEASES_CLOUD_STORAGE_PATH


def GetArchivePath(remote_name):
    return f'{buildbot.BuilderName()}/{buildbot.BuildNumber()}/{remote_name}'


def Upload(local, remote):
    """Upload file to Cloud Storage."""
    if not buildbot.IsUploadingBot():
        return
    remote = GetCloudStoragePath() + remote
    proc.check_call(['gsutil.py', 'cp', local, 'gs://' + remote])
    return CLOUD_STORAGE_BASE_URL + remote


def ListBuilds(revision):
    builds = []
    for builder in ('linux', 'mac', 'win'):
        try:
            os_builds = proc.check_output(
                ['gsutil.py', 'ls',
                 f'gs://{GetCloudStoragePath()}{builder}/{revision}'
                 ]).decode().strip().split('\n')
        except proc.CalledProcessError:
            os_builds = []
        builds += os_builds

    return builds


def UploadSkiaPerf(local, remote):
    """Upload file to Cloud Storage."""
    if not buildbot.IsUploadingBot():
        print('Not an uploading bot, not uploading skia perf results.')
        return
    remote = SKIA_PERF_STORAGE_PATH + remote
    proc.check_call(['gsutil.py', 'cp', local, 'gs://' + remote])
    return CLOUD_STORAGE_BASE_URL + remote


def Download(remote, local):
    remote = GetCloudStoragePath() + remote
    proc.check_call(['gsutil.py', 'cp', 'gs://' + remote, local])
