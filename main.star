#!/usr/bin/env lucicfg
# Copyright 2020 the V8 project authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

lucicfg.check_version("1.30.9", "Please update depot_tools")

# Use LUCI Scheduler BBv2 names and add Scheduler realms configs.
lucicfg.enable_experiment("crbug.com/1182002")

# Use python3 for all builds
luci.builder.defaults.experiments.set(
    {
        "luci.recipes.use_python3": 100,
    }
)


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
        "realms.cfg",
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
    bindings = [
        luci.binding(
            roles = "role/configs.validator",
            users = "emscripten-releases-try-bldr@chops-service-accounts.iam.gserviceaccount.com",
        ),
        luci.binding(
            roles = "role/swarming.poolOwner",
            groups = "mdb/v8-infra",
        ),
        luci.binding(
            roles = "role/swarming.poolViewer",
            groups = "all",
        ),
    ],
)

## Swarming permissions

# Allow admins to use LED and "Debug" button on every V8 builder and bot.
luci.binding(
    realm = "@root",
    roles = "role/swarming.poolUser",
    groups = "mdb/v8-infra",
)
luci.binding(
    realm = "@root",
    roles = "role/swarming.taskTriggerer",
    groups = "mdb/v8-infra",
)

# Allow cria/project-v8-led-users to use LED and "Debug" button on
# try and ci builders
def led_users(*, pool_realm, builder_realms, groups):
    luci.realm(
        name = pool_realm,
        bindings = [luci.binding(
            realm = pool_realm,
            roles = "role/swarming.poolUser",
            groups = groups,
        )],
    )
    for br in builder_realms:
        luci.binding(
            realm = br,
            roles = "role/swarming.taskTriggerer",
            groups = groups,
        )
led_users(
    pool_realm = "pools/ci",
    builder_realms = ["ci"],
    groups = "project-wasm-tools-admins",
)

led_users(
    pool_realm = "pools/try",
    builder_realms = ["try"],
    groups = "project-wasm-tools-admins",
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

ci_builder("linux", "Ubuntu")
ci_builder("linux-test-suites", "Ubuntu", max_concurrent_invocations = 2)
ci_builder("mac", "Mac")
ci_builder("win", "Windows-10")

try_builder("linux", "Ubuntu")
try_builder("mac", "Mac")
try_builder("win", "Windows-10")

luci.builder(
    name = "emscripten_releases_presubmit",
    bucket = "try",
    dimensions = {"os": "Ubuntu", "pool": "luci.emscripten-releases.try"},
    executable = luci.recipe(
        cipd_package = "infra/recipe_bundles/chromium.googlesource.com/chromium/tools/build",
        cipd_version = "refs/heads/main",
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
    ref = "refs/heads/main",
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
    refs = ["refs/heads/main"],
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
    refs = ["refs/heads/main"],
)
