Emscripten Releases
===================

This is meta-repository which brings together all the repositories needed to
produce and [emscripten](https://emscripten.org) release.  The revisions used
in each release are tracked in a `DEPS` file (See
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

Update a `DEPS` entry:

* `cd emscripten-releases`
* `git checkout -b <branch>`
* `roll-dep emscripten-releases/llvm-project`
* `git cl upload`

The argument to roll-dep must match one of the keys in the 'deps' dictionary in
the `DEPS` file. See `roll-dep -h` for more options.

༼ ༎ຶ ෴ ༎ຶ༽ Build and test scripts in `src/`
==========================================

This directory was forked from the WebAssembly
[waterfall repo](https://github.com/WebAssembly/waterfall.git) That repo was
retired because it was only used by emscripten-releases.

How do I run it?
----------------

1. Get the [sources](https://chromium.googlesource.com/emscripten-releases/)
2. Install `depot_tools`. Follow [the instructions](https://commondatastorage.googleapis.com/chrome-infra-docs/flat/depot_tools/docs/html/depot_tools_tutorial.html#_setting_up)
3. Install `pkg-config` if you don't have it installed already, e.g. `# apt install pkg-config`
4. Run build.py `python src/build.py`

Build.py has 3 types of actions:
* downloading/updating sources for tools and engines (sync)
* building those sources (build)
* running tests against them (test).

Each of these types has multiple steps (e.g. a build step for each component).
If you run build.py with no arguments, it will run all the sync, build, and test
steps. If you make a change and only want to run a subset of steps, you can
apply filters from the command line, via exclusions (to prevent specified steps
from running) or inclusions (to run only the specified steps). Sync, build, and
test exclusions are specified separately.  For example:

1. Do not sync any sources, build everything except LLVM, and run all tests:
  `$ src/build.py --no-sync --build-exclude=llvm`
2. Sync only binaryen, build LLVM and Binaryen, run everything other than the
   emscripten testsuites:
  `$ src/build.py --sync-include=binaryen --build-include=llvm,binaryen --test-exclude=emtest,emtest-asm`

The script should throw an error if you specify nonexistent steps or if you
specify both includes and excludes for the same type of action.

When run, the script creates a directory `src/work` inside the waterfall's git
checkout. All modifications are made inside this directory (checking and out and
building the sources, as well as the test builds and execution results). You can
also use the git checkouts (e.g. `src/work/llvm`) with your own branches; the
sync steps will check out the latest revision from the script's remote
repositories but will not overwrite or destroy any local work.
