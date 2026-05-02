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
  'binaryen_revision': 'e29edaea576a4ecba41d063b54d0ee5e5223820b',
  # Three lines of non-changing comments so that
  # the commit queue can handle CLs rolling emscripten
  # and whatever else without interference from each other.
  'emscripten_revision': '17a0b03d417233be4d034c60d78e59ce90b2c3f6',
  # Three lines of non-changing comments so that
  # the commit queue can handle CLs rolling llvm_project
  # and whatever else without interference from each other.
  'llvm_project_revision': '2548c010b0c866d3e1f1c398dfff228e33f4563c',
  # Three lines of non-changing comments so that
  # the commit queue can handle CLs rolling v8
  # and whatever else without interference from each other.
  'v8_revision': '25260052b4321cb6fc6cce66d333b58ca833787c',
  # Three lines of non-changing comments so that
  # the commit queue can handle CLs rolling llvm_test_suite
  # and whatever else without interference from each other.
  'llvm-test-suite_revision': '6c6a59906becace341d439cb7e45a56a4b96640a',
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
  'emscripten-releases/third_party/wasm-files': {
    'dep_type': 'gcs',
    'bucket': 'webassembly',
    'objects': [
      {
        'object_name': 'emscripten-releases-builds/deps/test-files/dart-pop.unopt.wasm',
        'sha256sum': '9ff90dc215c503224b56ecbaed9ce2db7d70c929281d3b0380ba921a239642e5',
        'size_bytes': 1330046,
        'generation': 1776963812644460,
        'output_file': 'dart-pop.unopt.wasm',
      },
      {
        'object_name': 'emscripten-releases-builds/deps/test-files/dart-flute-complex.unopt.wasm',
        'sha256sum': 'd63e2a789aad8af871124937ae8b64c28a0d1ca2b9131ec33ddde35cd7c9410a',
        'size_bytes': 4410188,
        'generation': 1776963981165463,
        'output_file': 'dart-flute-complex.unopt.wasm',
      }
    ]
  }
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
               'submodule', 'update', '--force', '--init'],
  },
]

recursedeps = [
  'v8'
]
