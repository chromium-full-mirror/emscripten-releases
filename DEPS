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
  'binaryen_revision': '365e6f239926e3da640014237b5420895ec247b9',
  # Three lines of non-changing comments so that
  # the commit queue can handle CLs rolling emscripten
  # and whatever else without interference from each other.
  'emscripten_revision': '408a6e9411165fdfd3c18163f37ee302e751857d',
  # Three lines of non-changing comments so that
  # the commit queue can handle CLs rolling fastcomp
  # and whatever else without interference from each other.
  'fastcomp_revision': '6c7e775325067e33fa60611e619a8b987b6d0c35',
  # Three lines of non-changing comments so that
  # the commit queue can handle CLs rolling fastcomp_clang
  # and whatever else without interference from each other.
  'fastcomp_clang_revision': '98df4be387dde3e3918fa5bbb5fc43e1a0e1daac',
  # Three lines of non-changing comments so that
  # the commit queue can handle CLs rolling llvm_project
  # and whatever else without interference from each other.
  'llvm_project_revision': '41bac76da873bf9b4b5d1353299ca68b4ad26ff3',
  # Three lines of non-changing comments so that
  # the commit queue can handle CLs rolling v8
  # and whatever else without interference from each other.
  'v8_revision': 'b33a8508ccad452b2581bf1e234b88b8871e6e5f',
  # Three lines of non-changing comments so that
  # the commit queue can handle CLs rolling wabt
  # and whatever else without interference from each other.
  'wabt_revision': 'af9250f743a52b374cef88bb3f78ec31c9f5eacf',
  # Three lines of non-changing comments so that
  # the commit queue can handle CLs rolling waterfall
  # and whatever else without interference from each other.
  'waterfall_revision': '3de5ced4417df532c6ef1de61b4f9e6bd47c8093',
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
