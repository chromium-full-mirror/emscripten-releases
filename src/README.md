# Waterfall

## ༼ ༎ຶ ෴ ༎ຶ༽ If it’s not tested, it’s already broken.

This directory was forked from the WebAssembly
[waterfall repo](https://github.com/WebAssembly/waterfall.git) That repo was
retired because it was only used by emscripten-releases.

# How do I run it?

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
2. Sync only WABT, build WABT and Binaryen, run everything other than the
   emscripten testsuites:
  `$ src/build.py --sync-include=wabt --build-include=wabt,binaryen --test-exclude=emtest,emtest-asm`

The script should throw an error if you specify nonexistent steps or if you
specify both includes and excludes for the same type of action.

When run, the script creates a directory `src/work` inside the waterfall's git
checkout. All modifications are made inside this directory (checking and out and
building the sources, as well as the test builds and execution results). You can
also use the git checkouts (e.g. `src/work/llvm`) with your own branches; the
sync steps will check out the latest revision from the script's remote
repositories but will not overwrite or destroy any local work.
