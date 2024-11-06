# Copyright 2019 the V8 project authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.


vars = {
  'binaryen_url': 'https://chromium.googlesource.com/external/github.com/WebAssembly/binaryen',
  'emscripten_url': 'https://chromium.googlesource.com/external/github.com/emscripten-core/emscripten',
  'llvm_project_url': 'https://chromium.googlesource.com/external/github.com/llvm/llvm-project',
  'v8_url': 'https://chromium.googlesource.com/v8/v8',
  # WARNING: This is a mirror of the old LLVM git mirror of the SVN repo. The github
  # repo URL is different, and has different hashes.
  'llvm-test-suite_url': 'https://chromium.googlesource.com/native_client/pnacl-llvm-testsuite',
  # TODO: v8 for testing, Gcc for torture tests, Update llvm test-suite to github

  # Three lines of non-changing comments so that
  # the commit queue can handle CLs rolling binaryen
  # and whatever else without interference from each other.
  'binaryen_revision': '92917c28ea6ef017e71a8a97eb364ed20bc52fe2',
  # Three lines of non-changing comments so that
  # the commit queue can handle CLs rolling emscripten
  # and whatever else without interference from each other.
  'emscripten_revision': '94f41734f1e9f74a19ac209e35e803ca29fcdd25',
  # Three lines of non-changing comments so that
  # the commit queue can handle CLs rolling llvm_project
  # and whatever else without interference from each other.
  'llvm_project_revision': 'f4270045f49d4936cd1d60e49f780ae9b1c18fab',
  # Three lines of non-changing comments so that
  # the commit queue can handle CLs rolling v8
  # and whatever else without interference from each other.
  'v8_revision': 'bcdc2ddd34ba24fc6d0b5651eec57d5295e51a71',
  # Three lines of non-changing comments so that
  # the commit queue can handle CLs rolling llvm_test_suite
  # and whatever else without interference from each other.
  'llvm-test-suite_revision': 'edc9be64895f43c79aa34fad32801ada216ce229',
}

deps = {
  'emscripten-releases/binaryen': Var('binaryen_url') + '@' + Var('binaryen_revision'),
  'emscripten-releases/emscripten': Var('emscripten_url') + '@' + Var('emscripten_revision'),
  'emscripten-releases/llvm-project': Var('llvm_project_url') + '@' + Var('llvm_project_revision'),
  'v8': Var('v8_url') + '@' + Var('v8_revision'),
  'emscripten-releases/llvm-test-suite': Var('llvm-test-suite_url') + '@' + Var('llvm-test-suite_revision'),
  'emscripten-releases/third_party/ninja': {
    'packages': [
      {
        'package': 'infra/3pp/tools/ninja/${{platform}}',
        'version': 'version:2@1.12.1.chromium.4',
      }
    ],
    'dep_type': 'cipd',
  },
}

hooks = [
  {
    'name': 'cmake',
    'pattern': '.',
    'action': ['python3', 'emscripten-releases/src/build.py',
               '--sync-include=cmake,nodejs,sysroot',
               '--prebuilt-dir=emscripten-releases', '--v8-dir=v8'],
  },
  {
    'name': 'binaryen_submodule_init',
    'pattern': '.',
    'action': ['git', '-C', 'emscripten-releases/binaryen',
               'submodule', 'update', '--init'],
  },
    {
    'name': 'emscripten_submodule_sync',
    'pattern': '.',
    'action': ['git', '-C', 'emscripten-releases/emscripten',
               'submodule', 'sync'],
  },
  {
    'name': 'emscripten_submodule_init',
    'pattern': '.',
    'action': ['git', '-C', 'emscripten-releases/emscripten',
               'submodule', 'update', '--init'],
  },
]

recursedeps = [
  'v8'
]
