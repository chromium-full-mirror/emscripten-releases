# Generated Wasm Files

This folder contains Wasm files that are used for benchmarking. The files are stored in a Google Cloud
Storage bucket and automatically downloaded when running `gclient sync`.

## Adding a New Wasm File

Generate your Wasm file, then upload it to GCS using the following script from `depot_tools`:

```bash
upload_to_google_storage_first_class.py -b webassembly --prefix=emscripten-releases-builds/deps/test-files third_party/wasm-files/dart-flute-complex.unopt.wasm -o dart-flute-complex.unopt.wasm
```

The above command will output some JSON. Copy the entry in the `objects` array into the DEPS file
where other objects are defined. **You'll also want to add an `output_file` key with the desired
filename**, e.g., `output_file: 'dart-flute-complex.unopt.wasm'`.


```json
{
  "path": {
    "dep_type": "gcs",
    "bucket": "webassembly",
    "objects": [
      {
        "object_name": "emscripten-releases-builds/deps/test-files/dart-flute-complex.unopt.wasm",
        "sha256sum": "d63e2a789aad8af871124937ae8b64c28a0d1ca2b9131ec33ddde35cd7c9410a",
        "size_bytes": 4410188,
        "generation": 1776963981165463
      }
    ]
  }
}
```

## Building Dart Benchmarks

### Pop

* Get the repository [https://github.com/dart-lang/sample-pop_pop_win](https://github.com/dart-lang/sample-pop_pop_win) which is a public Dart sample app.
* Get the public Dart SDK. On Linux, get the deb and do dpkg -i: [go/dart-install#glinux-open-source](http://goto.google.com/dart-install#glinux-open-source)
* **`dart pub get`**
* **`dart compile wasm web/main.dart --extra-compiler-option=--save-unopt -o main.wasm`**
* There should now be **main.unopt.wasm** alongside **main.wasm**. The unoptimized one is the one that wasm-opt is run on, so we benchmark that.

### Flute

* **git clone [https://github.com/dart-lang/flute](https://github.com/dart-lang/flute)**
* In the repository, **cd benchmarks**
* **dart pub get**
* **dart compile wasm --extra-compiler-option=--save-unopt lib/complex.dart -o complex.wasm**
* Get **complex.unopt.wasm**
