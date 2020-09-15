# Copyright 2020 the V8 project authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

load(
    "//lib.star",
    "ci_builder",
    "emscripten_cq_group",
    "try_builder",
)

lucicfg.config(
    config_dir = "generated",
    tracked_files = [
        "cr-buildbucket.cfg",
        "project.cfg",
        "commit-queue.cfg",
        "luci-logdog.cfg",
        "luci-milo.cfg",
        "luci-scheduler.cfg",
    ],
    fail_on_warnings = True,
)

luci.project(
    name = "emscripten-releases",
    buildbucket = "cr-buildbucket.appspot.com",
    logdog = "luci-logdog",
    milo = "luci-milo",
    notify = "luci-notify.appspot.com",
    scheduler = "luci-scheduler",
    swarming = "chromium-swarm.appspot.com",
    acls = [
        acl.entry(
            [
                acl.BUILDBUCKET_READER,
                acl.LOGDOG_READER,
                acl.PROJECT_CONFIGS_READER,
                acl.SCHEDULER_READER,
            ],
            groups = ["all"],
        ),
        acl.entry([acl.SCHEDULER_OWNER], groups = ["project-wasm-tools-admins"]),
        acl.entry([acl.LOGDOG_WRITER], groups = ["luci-logdog-chromium-writers"]),
    ],
)

luci.logdog(
    gs_bucket = "chromium-luci-logdog",
)

luci.bucket(name = "ci", acls = [
    acl.entry(
        [acl.BUILDBUCKET_TRIGGERER],
        users = [
            "luci-scheduler@appspot.gserviceaccount.com",
            "emscripten-releases-ci-builder@chops-service-accounts.iam.gserviceaccount.com",
        ],
    ),
    acl.entry(
        [acl.SCHEDULER_READER],
        groups = ["all"],
    ),
])

luci.bucket(name = "try", acls = [
    acl.entry(
        [acl.BUILDBUCKET_TRIGGERER],
        groups = ["service-account-cq", "project-wasm-tools-committers"],
    ),
])

ci_builder("linux", "Ubuntu-16.04")
ci_builder("linux-test-suites", "Ubuntu-16.04", archive = False, max_concurrent_invocations = 2)
ci_builder("mac", "Mac")
ci_builder("win", "Windows-10")

try_builder("linux", "Ubuntu-16.04")
try_builder("mac", "Mac")
try_builder("win", "Windows-10")

luci.builder(
    name = "emscripten_releases_presubmit",
    bucket = "try",
    dimensions = {"os": "Ubuntu-16.04", "pool": "luci.emscripten-releases.try"},
    executable = luci.recipe(
        cipd_package = "infra/recipe_bundles/chromium.googlesource.com/chromium/tools/build",
        cipd_version = "refs/heads/master",
        name = "run_presubmit",
    ),
    service_account = "emscripten-releases-try-bldr@chops-service-accounts.iam.gserviceaccount.com",
    swarming_tags = ["vpython:native-python-wrapper"],
    execution_timeout = 600 * time.second,
    properties = {
        "runhooks": False,
        "solution_name": "emscripten-releases",
    },
    priority = 25,
)

luci.cq(
    submit_max_burst = 1,
    submit_burst_delay = 60 * time.second,
    status_host = "chromium-cq-status.appspot.com",
)

emscripten_cq_group(
    name = "infra-cq",
    ref = "refs/heads/infra/config",
    verifiers = [luci.cq_tryjob_verifier("emscripten_releases_presubmit", disable_reuse = True)],
)

emscripten_cq_group(
    name = "emscripten-releases-cq",
    ref = "refs/heads/master",
    verifiers = [
        luci.cq_tryjob_verifier("emscripten_releases_presubmit", disable_reuse = True),
        "try/linux",
        "try/mac",
        "try/win",
    ],
)

luci.milo(
    logo = "https://storage.googleapis.com/chrome-infra-public/logo/emscripten.svg",
)

luci.console_view(
    name = "main",
    title = "Main",
    repo = "https://chromium.googlesource.com/emscripten-releases",
    refs = ["refs/heads/master"],
    favicon = "https://storage.googleapis.com/chrome-infra-public/logo/emscripten.ico",
    entries = [
        luci.console_view_entry(builder = "ci/linux", short_name = "Linux", category = "Release builders"),
        luci.console_view_entry(builder = "ci/mac", short_name = "Mac", category = "Release builders"),
        luci.console_view_entry(builder = "ci/win", short_name = "Windows", category = "Release builders"),
        luci.console_view_entry(builder = "linux-test-suites", short_name = "Test suites", category = "Testers"),
    ],
)

luci.list_view(
    name = "tryserver",
    title = "Tryserver",
    favicon = "https://storage.googleapis.com/chrome-infra-public/logo/emscripten.ico",
    entries = [
        "emscripten_releases_presubmit",
        "try/linux",
        "try/mac",
        "try/win",
    ],
)

luci.gitiles_poller(
    name = "emscripten-releases-trigger",
    bucket = "ci",
    repo = "https://chromium.googlesource.com/emscripten-releases",
    refs = ["refs/heads/master"],
)
