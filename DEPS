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
  # TODO: v8 for testing, Gcc for torture tests, llvm test-suite

  # Three lines of non-changing comments so that
  # the commit queue can handle CLs rolling binaryen
  # and whatever else without interference from each other.
  'binaryen_revision': 'c57f93c8919ab33574e5ce78f0044980ca33de76',
  # Three lines of non-changing comments so that
  # the commit queue can handle CLs rolling emscripten
  # and whatever else without interference from each other.
  'emscripten_revision': '94b1555a09f869d65354a2033da724ce77a43106',
  # Three lines of non-changing comments so that
  # the commit queue can handle CLs rolling fastcomp
  # and whatever else without interference from each other.
  'fastcomp_revision': '1b4148f39a69c7fc62edadd85e4122b68694dfb7',
  # Three lines of non-changing comments so that
  # the commit queue can handle CLs rolling fastcomp_clang
  # and whatever else without interference from each other.
  'fastcomp_clang_revision': '98df4be387dde3e3918fa5bbb5fc43e1a0e1daac',
  # Three lines of non-changing comments so that
  # the commit queue can handle CLs rolling llvm_project
  # and whatever else without interference from each other.
  'llvm_project_revision': 'f12d56f2638d7402d94efb6081e972ea3e819fcc',
  # Three lines of non-changing comments so that
  # the commit queue can handle CLs rolling v8
  # and whatever else without interference from each other.
  'v8_revision': '4c8ffcbe3959f4a1b799bb9d6b7ef9b49bf6d144',
  # Three lines of non-changing comments so that
  # the commit queue can handle CLs rolling wabt
  # and whatever else without interference from each other.
  'wabt_revision': '04fd00d2fc29b565da350739d3a1f9c85267d5d2',
  # Three lines of non-changing comments so that
  # the commit queue can handle CLs rolling waterfall
  # and whatever else without interference from each other.
  'waterfall_revision': 'fe3feca48ae596780282d9fc36f876b9a3131688',
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
