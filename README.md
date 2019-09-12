Emscripten Releases
===================

This is meta-repository which brings together all the repositories needed to
produce and [emscripten](https://emscripten.org) release.  The revisions used
in each release are tracked in a DEPS file (See
[depot_tools](https://dev.chromium.org/developers/how-tos/depottools for more
information).  This file contains a history of revisions that have been built
and tested together and represent a known good state.

Each release is automatically built and uploaded to to Google Cloud Storage and
can be used standalone or with [emsdk](https://github.com/emscripten-core/emsdk).

The build status for the automated builds can be seen
[here](https://ci.chromium.org/p/emscripten-releases/g/main/console)

Updating DEPS entries
---------------------

Install [depot_tools](https://www.chromium.org/developers/how-tos/depottools)
and then check out: `gclient config
https://chromium.googlesource.com/emscripten-releases` (Do this only once)

Update working trees:

* `git pull`
* `gclient sync`

Update a DEPS entry:

* `cd emscripten-releases`
* `git checkout -b <branch>`
* `roll-dep emscripten-releases/llvm-project`
* `git cl upload`

The argument to roll-dep must match one of the keys in the 'deps' dictionary in
the DEPS file. See `roll-dep -h` for more options.

The following DEPS entries do not track `origin/master` but instead track
`origin/incoming`:

* emscripten-fastcomp
* emscripten-fastcomp-clang
* emscripten

To roll these DEPS entries you also need to specify the branch name.  e.g.:

* `roll-dep emscripten-releases/emscripten --roll-to origin/incoming`
