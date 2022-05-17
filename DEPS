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
  'binaryen_revision': 'f81fcd92557e6389d719b7d63f845434810a91fe',
  # Three lines of non-changing comments so that
  # the commit queue can handle CLs rolling emscripten
  # and whatever else without interference from each other.
  'emscripten_revision': 'e8a13ae4f7e03158f122214022062b7a08dd2d78',
  # Three lines of non-changing comments so that
  # the commit queue can handle CLs rolling llvm_project
  # and whatever else without interference from each other.
  'llvm_project_revision': 'c1a9d14982f887355da1959eba3a47b952fc6e7a',
  # Three lines of non-changing comments so that
  # the commit queue can handle CLs rolling v8
  # and whatever else without interference from each other.
  'v8_revision': '93446e3c12b0df604bd3925fbc51b33d499e9be8',
  # Three lines of non-changing comments so that
  # the commit queue can handle CLs rolling llvm_test_suite
  # and whatever else without interference from each other.
  'llvm-test-suite_revision': 'fb038dea9c4b0e26a584dd1e9860deb62e5847c3',
}

deps = {
  'emscripten-releases/binaryen': Var('binaryen_url') + '@' + Var('binaryen_revision'),
  'emscripten-releases/emscripten': Var('emscripten_url') + '@' + Var('emscripten_revision'),
  'emscripten-releases/llvm-project': Var('llvm_project_url') + '@' + Var('llvm_project_revision'),
  'v8': Var('v8_url') + '@' + Var('v8_revision'),
  'emscripten-releases/llvm-test-suite': Var('llvm-test-suite_url') + '@' + Var('llvm-test-suite_revision'),
}

hooks = [
  {
    'name': 'cmake',
    'pattern': '.',
    'action': ['python3', 'emscripten-releases/src/build.py',
               '--sync-include=cmake,nodejs,sysroot','--no-build', '--no-test',
               '--prebuilt-dir=emscripten-releases', '--v8-dir=v8'],
  },
  {
    'name': 'binaryen_submodule_init',
    'pattern': '.',
    'action': ['git', '-C', 'emscripten-releases/binaryen',
               'submodule', 'update', '--init'],
  },
]

recursedeps = [
  'v8'
]
