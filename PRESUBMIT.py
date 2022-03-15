# Copyright 2019 the V8 project authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Presubmit script for changes in emscripten-releases.
See http://dev.chromium.org/developers/how-tos/depottools/presubmit-scripts
for more details about the presubmit API built into gcl.
"""

import json


USE_PYTHON3 = True

def _CheckJSONFiles(input_api, output_api):
  def FilterFile(affected_file):
    return input_api.FilterSourceFile(
        affected_file,
        files_to_check=(r'.+\.json',))

  results = []
  for f in input_api.AffectedFiles(
      file_filter=FilterFile, include_deletes=False):
    with open(f.LocalPath()) as j:
      try:
        json.load(j)
      except Exception as e:
        results.append(
            'JSON validation failed for %s. Error:\n%s' % (f.LocalPath(), e))

  return [output_api.PresubmitError(r) for r in results]


def _CommonChecks(input_api, output_api):
  """Checks common to both upload and commit."""
  results = []
  results.extend(_CheckJSONFiles(input_api, output_api))
  return results


def CheckChangeOnUpload(input_api, output_api):
  results = []
  results.extend(_CommonChecks(input_api, output_api))
  return results


def CheckChangeOnCommit(input_api, output_api):
  results = []
  results.extend(_CommonChecks(input_api, output_api))
  return results
