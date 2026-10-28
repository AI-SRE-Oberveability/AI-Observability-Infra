"""Fail closed before cloud authentication; never print supplied configuration values."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import uuid
from datetime import date
from decimal import Decimal, InvalidOperation

REPOSITORY = "AI-SRE-Oberveability/AI-Observability-Infra"


def dispatch(values):
    if values.get("GITHUB_REPOSITORY") != REPOSITORY:
        raise ValueError(
            "Deployment repository does not match the approved infra repository"
        )
    if values.get("GITHUB_EVENT_NAME") != "workflow_dispatch":
        raise ValueError("Only manual workflow_dispatch can deploy")
    if values.get("GITHUB_REF") != "refs/heads/main":
        raise ValueError("Only the main branch can plan or apply")
    if values.get("AZURE_DEPLOYMENT_ENABLED") != "true":
        raise ValueError(
            "Azure execution is disabled; confirm personal targets, budget and G2/G3 first"
        )
    if values.get("OPERATION") not in {"plan", "apply"}:
        raise ValueError("Operation must be plan or apply")
    if values["OPERATION"] == "apply" and not re.fullmatch(
        r"[a-f0-9]{64}", values.get("REVIEWED_PLAN_SHA256", "")
    ):
        raise ValueError("Apply requires the fingerprint of a previously reviewed plan")


def targets(values):
    required = [
        "AZURE_CLIENT_ID",
        "AZURE_TENANT_ID",
        "AZURE_SUBSCRIPTION_ID",
        "TF_STATE_RESOURCE_GROUP",
        "TF_STATE_STORAGE_ACCOUNT",
        "TF_STATE_CONTAINER",
        "LAB_RESOURCE_GROUP",
        "AZURE_LOCATION",
        "LAB_EXPIRES_ON",
        "AZURE_MONTHLY_BUDGET",
        "AZURE_BUDGET_CURRENCY",
    ]
    missing = [key for key in required if not values.get(key)]
    if missing:
        raise ValueError("Missing approved configuration: " + ", ".join(missing))
    for key in ["AZURE_CLIENT_ID", "AZURE_TENANT_ID", "AZURE_SUBSCRIPTION_ID"]:
        try:
            parsed = uuid.UUID(values[key])
        except ValueError:
            raise ValueError(key + " must be a confirmed UUID") from None
        if not parsed.int:
            raise ValueError(key + " cannot use an all-zero placeholder")
    for key in ["LAB_RESOURCE_GROUP", "TF_STATE_RESOURCE_GROUP"]:
        if not re.fullmatch(r"rg-ai-sre-[a-z0-9][a-z0-9-]{1,40}", values[key]):
            raise ValueError(key + " must use the dedicated rg-ai-sre- prefix")
    if values["LAB_RESOURCE_GROUP"] == values["TF_STATE_RESOURCE_GROUP"]:
        raise ValueError(
            "Bootstrap state and lab resources must have separate resource groups"
        )
    if not re.fullmatch(r"[a-z0-9]{3,24}", values["TF_STATE_STORAGE_ACCOUNT"]):
        raise ValueError("TF_STATE_STORAGE_ACCOUNT has an invalid format")
    if not re.fullmatch(
        r"[a-z0-9][a-z0-9-]{1,61}[a-z0-9]", values["TF_STATE_CONTAINER"]
    ):
        raise ValueError("TF_STATE_CONTAINER has an invalid format")
    if not re.fullmatch(r"[a-z][a-z0-9]+", values["AZURE_LOCATION"]):
        raise ValueError("AZURE_LOCATION must be a confirmed region name")
    try:
        expiry = date.fromisoformat(values["LAB_EXPIRES_ON"])
    except ValueError:
        raise ValueError("LAB_EXPIRES_ON must be a valid YYYY-MM-DD date") from None
    if expiry <= date.today():
        raise ValueError("LAB_EXPIRES_ON must be in the future")
    try:
        budget = Decimal(values["AZURE_MONTHLY_BUDGET"])
    except InvalidOperation:
        raise ValueError(
            "AZURE_MONTHLY_BUDGET must be a positive finite amount"
        ) from None
    if not budget.is_finite() or budget <= 0:
        raise ValueError("AZURE_MONTHLY_BUDGET must be a positive finite amount")
    if not re.fullmatch(r"[A-Z]{3}", values["AZURE_BUDGET_CURRENCY"]):
        raise ValueError("AZURE_BUDGET_CURRENCY must be a three-letter currency code")


def context(values, account):
    if (
        account.get("id") != values.get("AZURE_SUBSCRIPTION_ID")
        or account.get("tenantId") != values.get("AZURE_TENANT_ID")
        or account.get("state") != "Enabled"
    ):
        raise ValueError(
            "Authenticated Azure context does not match the confirmed personal target"
        )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("check", choices=["dispatch", "targets", "context"])
    args = parser.parse_args()
    try:
        if args.check == "context":
            context(os.environ, json.load(sys.stdin))
        else:
            {"dispatch": dispatch, "targets": targets}[args.check](os.environ)
    except ValueError as error:
        raise SystemExit(str(error)) from None
    print(args.check + " guard passed; configuration values are not logged")


if __name__ == "__main__":
    main()
