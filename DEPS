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
  'binaryen_revision': '39e3490793919261d11921b7490e252e35ca278a',
  # Three lines of non-changing comments so that
  # the commit queue can handle CLs rolling emscripten
  # and whatever else without interference from each other.
  'emscripten_revision': '13b1f81e1ef6089321fc4ac1a3a2aa273d436b89',
  # Three lines of non-changing comments so that
  # the commit queue can handle CLs rolling llvm_project
  # and whatever else without interference from each other.
  'llvm_project_revision': '823ddba1b325f30fc3fb2e9d695c211b856a4d5d',
  # Three lines of non-changing comments so that
  # the commit queue can handle CLs rolling v8
  # and whatever else without interference from each other.
  'v8_revision': '0ddc9258ec100669608a6673fd9a7094775be7bf',
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
        'version': 'version:2@1.8.2.chromium.3',
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
