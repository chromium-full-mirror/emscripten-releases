# Copyright 2020 the V8 project authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

def emscripten_builder(bucket, name, os, service_account, **kwargs):
    caches = None
    goma_props = {
        "server_host": "goma.chromium.org",
        "enable_ats": True,
        "rpc_extra_params": "?prod",
        "use_luci_auth": True,
    }
    reclient_props = {
        "instance": "rbe-chromium-trusted" if bucket == "ci" else "rbe-chromium-untrusted",
        "metrics_project": "chromium-reclient-metrics",
        "scandeps_server": True,
    }
    if os.startswith("Mac"):
        goma_props.pop("enable_ats")
        caches = [
            swarming.cache(
                path = "osx_sdk",
                name = "osx_sdk",
            ),
        ]

    props = {"$build/goma": goma_props}
    if not os.lower().startswith("windows") and not os.lower().startswith("mac"):
        props.update({"$build/reclient": reclient_props})
    luci.builder(
        name = name,
        bucket = bucket,
        caches = caches,
        dimensions = {"os": os, "pool": "luci.emscripten-releases." + bucket},
        executable = luci.recipe(
            cipd_package = "infra/recipe_bundles/chromium.googlesource.com/chromium/tools/build",
            cipd_version = "refs/heads/main",
            name = "emscripten_releases",
        ),
        service_account = service_account,
        swarming_tags = ["vpython:native-python-wrapper"],
        execution_timeout = 25200 * time.second,
        properties = props,
        **kwargs
    )

def ci_builder(name, os, max_concurrent_invocations = 4):
    emscripten_builder(
        "ci",
        name,
        os,
        "emscripten-releases-ci-builder@chops-service-accounts.iam.gserviceaccount.com",
        triggered_by = ["emscripten-releases-trigger"],
        triggering_policy = scheduler.policy(
            kind = scheduler.GREEDY_BATCHING_KIND,
            max_concurrent_invocations = max_concurrent_invocations,
        ),
    )

def try_builder(name, os):
    emscripten_builder(
        "try",
        name,
        os,
        "emscripten-releases-try-bldr@chops-service-accounts.iam.gserviceaccount.com",
        priority = 30,
    )

def emscripten_cq_group(name, ref, verifiers):
    luci.cq_group(
        name = name,
        watch = cq.refset(
            repo = "https://chromium.googlesource.com/emscripten-releases",
            refs = [ref],
        ),
        acls = [
            acl.entry(
                [acl.CQ_COMMITTER, acl.CQ_DRY_RUNNER],
                groups = ["project-wasm-tools-committers"],
            ),
        ],
        retry_config = cq.retry_config(
            single_quota = 1,
            global_quota = 2,
            failure_weight = 2,
            transient_failure_weight = 1,
            timeout_weight = 4,
        ),
        verifiers = verifiers,
    )
