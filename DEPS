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
  'binaryen_revision': 'a7d93efd82d3c04ff835dbd4d3b619f8f6a4e4ce',
  # Three lines of non-changing comments so that
  # the commit queue can handle CLs rolling emscripten
  # and whatever else without interference from each other.
  'emscripten_revision': 'e42d14bf103a4461faef8ab009b7b58c0ac48bdd',
  # Three lines of non-changing comments so that
  # the commit queue can handle CLs rolling llvm_project
  # and whatever else without interference from each other.
  'llvm_project_revision': 'f82283a84ed897f06a1aaac028accbad0d5057c7',
  # Three lines of non-changing comments so that
  # the commit queue can handle CLs rolling v8
  # and whatever else without interference from each other.
  'v8_revision': '760fdf9bcdaaa4d806c761c479780ef229fc636a',
  # Three lines of non-changing comments so that
  # the commit queue can handle CLs rolling llvm_test_suite
  # and whatever else without interference from each other.
  'llvm-test-suite_revision': 'e6f67406a1368ccff66e880af3297712be7a0fd9',
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
