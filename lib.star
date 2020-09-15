def emscripten_builder(bucket, name, os, service_account, archive = None, **kwargs):
    goma_props = {
        "server_host": "goma.chromium.org",
        "enable_ats": True,
        "rpc_extra_params": "?prod",
    }
    if os.startswith("Mac"):
        goma_props.pop("enable_ats")
    props = {"$build/goma": goma_props}
    if archive != None:
        props["archive"] = archive
    luci.builder(
        name = name,
        bucket = bucket,
        dimensions = {"os": os, "pool": "luci.emscripten-releases." + bucket},
        executable = luci.recipe(
            cipd_package = "infra/recipe_bundles/chromium.googlesource.com/chromium/tools/build",
            cipd_version = "refs/heads/master",
            name = "emscripten_releases",
        ),
        service_account = service_account,
        swarming_tags = ["vpython:native-python-wrapper"],
        execution_timeout = 7201 * time.second,
        properties = props,
        **kwargs
    )

def ci_builder(name, os, archive = None, max_concurrent_invocations = 4):
    emscripten_builder(
        "ci",
        name,
        os,
        "emscripten-releases-ci-builder@chops-service-accounts.iam.gserviceaccount.com",
        archive = archive,
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
