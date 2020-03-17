# Copyright 2019 the V8 project authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

vars = {
  'binaryen_url': 'https://chromium.googlesource.com/external/github.com/WebAssembly/binaryen',
  'emscripten_url': 'https://chromium.googlesource.com/external/github.com/emscripten-core/emscripten',
  'fastcomp_url': 'https://chromium.googlesource.com/external/github.com/emscripten-core/emscripten-fastcomp',
  'fastcomp_clang_url': 'https://chromium.googlesource.com/external/github.com/emscripten-core/emscripten-fastcomp-clang',
  'llvm_project_url': 'https://chromium.googlesource.com/external/github.com/llvm/llvm-project',
  'v8_url': 'https://chromium.googlesource.com/v8/v8',
  'wabt_url': 'https://chromium.googlesource.com/external/github.com/WebAssembly/wabt',
  'waterfall_url': 'https://chromium.googlesource.com/external/github.com/WebAssembly/waterfall',
  # WARNING: This is a mirror of the old LLVM git mirror of the SVN repo. The github
  # repo URL is different, and has different hashes.
  'llvm-test-suite_url': 'https://chromium.googlesource.com/external/llvm.org/test-suite',
  # TODO: v8 for testing, Gcc for torture tests, Update llvm test-suite to github

  # Three lines of non-changing comments so that
  # the commit queue can handle CLs rolling binaryen
  # and whatever else without interference from each other.
  'binaryen_revision': '38a795c48e269b92a1e6c54682a436ce23339a8d',
  # Three lines of non-changing comments so that
  # the commit queue can handle CLs rolling emscripten
  # and whatever else without interference from each other.
  'emscripten_revision': '4b6eba96c40e58e83aa1c45dc565ac4e312cc6f7',
  # Three lines of non-changing comments so that
  # the commit queue can handle CLs rolling fastcomp
  # and whatever else without interference from each other.
  'fastcomp_revision': 'b4837f88af2d240abb550c0bbd47f3b8ffe5985a',
  # Three lines of non-changing comments so that
  # the commit queue can handle CLs rolling fastcomp_clang
  # and whatever else without interference from each other.
  'fastcomp_clang_revision': '98df4be387dde3e3918fa5bbb5fc43e1a0e1daac',
  # Three lines of non-changing comments so that
  # the commit queue can handle CLs rolling llvm_project
  # and whatever else without interference from each other.
  'llvm_project_revision': 'd9a012ed8a5a12be0c96fe325aec893c7fc6d288',
  # Three lines of non-changing comments so that
  # the commit queue can handle CLs rolling v8
  # and whatever else without interference from each other.
  'v8_revision': 'bc6ebfec81c2b01d66966a4c1a24015ec25dfc51',
  # Three lines of non-changing comments so that
  # the commit queue can handle CLs rolling wabt
  # and whatever else without interference from each other.
  'wabt_revision': 'c47cd5cf72d7aca083184fc18fd6d155f20b2b4f',
  # Three lines of non-changing comments so that
  # the commit queue can handle CLs rolling waterfall
  # and whatever else without interference from each other.
  'waterfall_revision': '46974c0fdda398f9c4e0394607fe971a27828f43',
  # Three lines of non-changing comments so that
  # the commit queue can handle CLs rolling llvm_test_suite
  # and whatever else without interference from each other.
  'llvm-test-suite_revision': '8f3667acb3a6438c8088302b94a8bdbf7662623f',
}

deps = {
  'emscripten-releases/binaryen': Var('binaryen_url') + '@' + Var('binaryen_revision'),
  'emscripten-releases/emscripten': Var('emscripten_url') + '@' + Var('emscripten_revision'),
  'emscripten-releases/emscripten-fastcomp': Var('fastcomp_url') + '@' + Var('fastcomp_revision'),
  'emscripten-releases/emscripten-fastcomp-clang': Var('fastcomp_clang_url') + '@' + Var('fastcomp_clang_revision'),
  'emscripten-releases/llvm-project': Var('llvm_project_url') + '@' + Var('llvm_project_revision'),
  'v8': Var('v8_url') + '@' + Var('v8_revision'),
  'emscripten-releases/wabt': Var('wabt_url') + '@' + Var('wabt_revision'),
  'emscripten-releases/waterfall': Var('waterfall_url') + '@' + Var('waterfall_revision'),
  'emscripten-releases/llvm-test-suite': Var('llvm-test-suite_url') + '@' + Var('llvm-test-suite_revision'),
}

hooks = [
  {
    'name': 'cmake',
    'pattern': '.',
    'action': ['python', 'emscripten-releases/waterfall/src/build.py',
               '--sync-include=cmake,nodejs,java','--no-build', '--no-test',
               '--prebuilt-dir=emscripten-releases', '--v8-dir=v8'],
  },
]

recursedeps = [
  'v8'
]
