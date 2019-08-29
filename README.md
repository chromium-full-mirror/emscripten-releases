This repo contains a DEPS file (used by
[depot_tools](https://dev.chromium.org/developers/how-tos/depottools)) with dependencies for building a package of
[emscripten](https://emscripten.org). The package is uploaded to Google
Cloud Storage and can be used standalone or with [emsdk](https://github.com/emscripten-core/emsdk).

The build status for the automated builds can be seen [here](https://ci.chromium.org/p/emscripten-releases/g/main/console)

### DEPS update cheat sheet:

Install [depot_tools](https://www.chromium.org/developers/how-tos/depottools) and then check out:
`gclient config https://chromium.googlesource.com/emscripten-releases`
(Do this only once)

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
