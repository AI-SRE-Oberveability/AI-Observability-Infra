"""Publish only a plan fingerprint/counts; require a reviewed match before apply."""

from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
import re
from collections import Counter
from pathlib import Path


def review(plan, source, operation="plan", expected=""):
    if not re.fullmatch(r"[a-f0-9]{40}", source):
        raise ValueError("A full source commit is required")
    if plan.get("errored") or plan.get("terraform_version") != "1.17.1":
        raise ValueError(
            "Plan failed or was produced by an unexpected Terraform version"
        )
    counts = Counter()
    for change in plan.get("resource_changes", []):
        if (
            change.get("address") != "azurerm_resource_group.lab"
            or change.get("mode") != "managed"
            or change.get("provider_name") != "registry.terraform.io/hashicorp/azurerm"
        ):
            raise ValueError("Plan exceeds the single approved foundation resource")
        actions = change["change"]["actions"]
        if actions not in [["create"], ["update"], ["no-op"]]:
            raise ValueError(
                "Delete, replacement or unsupported actions require a separate reviewed change"
            )
        counts[actions[0]] += 1
    # Timestamp is intentionally excluded. Values remain private, but changes to
    # configuration, prior state, variables, planned values or source invalidate approval.
    payload = {key: value for key, value in plan.items() if key != "timestamp"}
    canonical = json.dumps(
        {"source": source, "plan": payload},
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode()
    digest = hashlib.sha256(canonical).hexdigest()
    if operation == "apply":
        if not re.fullmatch(r"[a-f0-9]{64}", expected) or not hmac.compare_digest(
            digest, expected
        ):
            raise ValueError(
                "Plan/source/state changed or no reviewed fingerprint supplied; review a new plan"
            )
    elif operation != "plan":
        raise ValueError("Unsupported operation")
    return {
        "source_commit": source,
        "plan_sha256": digest,
        "action_counts": dict(counts),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plan_json", type=Path)
    args = parser.parse_args()
    try:
        result = review(
            json.loads(args.plan_json.read_text(encoding="utf-8")),
            os.environ["GITHUB_SHA"],
            os.environ["OPERATION"],
            os.environ.get("REVIEWED_PLAN_SHA256", ""),
        )
    except ValueError as error:
        raise SystemExit(str(error)) from None
    summary = "\n".join(
        [
            "## Terraform foundation plan",
            "",
            "Source commit: `" + result["source_commit"] + "`",
            "Reviewed plan SHA256: `" + result["plan_sha256"] + "`",
            "Action counts: `" + json.dumps(result["action_counts"]) + "`",
            "",
            "Resource values, raw plans and state are not published.",
            "",
        ]
    )
    print(summary)
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with Path(os.environ["GITHUB_STEP_SUMMARY"]).open(
            "a", encoding="utf-8"
        ) as stream:
            stream.write(summary)


if __name__ == "__main__":
    main()
