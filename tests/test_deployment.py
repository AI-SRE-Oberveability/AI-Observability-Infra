"""Safety checks for the unconfigured and later explicitly enabled delivery path."""

import copy
import json
import sys
import unittest
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from deployment_guard import context, dispatch, targets  # noqa: E402
from plan_review import review  # noqa: E402


class DeploymentChecks(unittest.TestCase):
    def test_cached_or_wrong_azure_context_is_rejected(self):
        account = {
            "id": self.targets["AZURE_SUBSCRIPTION_ID"],
            "tenantId": self.targets["AZURE_TENANT_ID"],
            "state": "Enabled",
        }
        context(self.targets, account)
        with self.assertRaises(ValueError):
            context(self.targets, {**account, "tenantId": "different-cached-tenant"})

    def setUp(self):
        self.dispatch = {
            "GITHUB_REPOSITORY": "AI-SRE-Oberveability/AI-Observability-Infra",
            "GITHUB_EVENT_NAME": "workflow_dispatch",
            "GITHUB_REF": "refs/heads/main",
            "AZURE_DEPLOYMENT_ENABLED": "true",
            "OPERATION": "plan",
        }
        self.targets = {
            "AZURE_CLIENT_ID": "11111111-1111-4111-8111-111111111111",
            "AZURE_TENANT_ID": "22222222-2222-4222-8222-222222222222",
            "AZURE_SUBSCRIPTION_ID": "33333333-3333-4333-8333-333333333333",
            "TF_STATE_RESOURCE_GROUP": "rg-ai-sre-state",
            "LAB_RESOURCE_GROUP": "rg-ai-sre-lab",
            "TF_STATE_STORAGE_ACCOUNT": "staisresynthetic",
            "TF_STATE_CONTAINER": "tfstate",
            "AZURE_LOCATION": "syntheticregion",
            "LAB_EXPIRES_ON": (date.today() + timedelta(days=7)).isoformat(),
            "AZURE_MONTHLY_BUDGET": "10",
            "AZURE_BUDGET_CURRENCY": "USD",
        }
        self.source = "a" * 40
        self.plan = {
            "terraform_version": "1.17.1",
            "timestamp": "one",
            "resource_changes": [
                {
                    "address": "azurerm_resource_group.lab",
                    "mode": "managed",
                    "provider_name": "registry.terraform.io/hashicorp/azurerm",
                    "change": {
                        "actions": ["create"],
                        "after": {"tags": {"canary": "PRIVATE-CANARY"}},
                    },
                }
            ],
        }

    def test_cloud_is_disabled_by_default(self):
        for value in [None, "false", "TRUE"]:
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(ValueError, "disabled"),
            ):
                dispatch({**self.dispatch, "AZURE_DEPLOYMENT_ENABLED": value})

    def test_forks_prs_and_nonmain_branches_cannot_deploy(self):
        for key, value in [
            ("GITHUB_REPOSITORY", "someone/fork"),
            ("GITHUB_EVENT_NAME", "pull_request"),
            ("GITHUB_REF", "refs/heads/untrusted"),
        ]:
            with self.subTest(key=key), self.assertRaises(ValueError):
                dispatch({**self.dispatch, key: value})

    def test_apply_requires_a_reviewed_fingerprint(self):
        with self.assertRaisesRegex(ValueError, "fingerprint"):
            dispatch({**self.dispatch, "OPERATION": "apply"})
        dispatch(
            {**self.dispatch, "OPERATION": "apply", "REVIEWED_PLAN_SHA256": "a" * 64}
        )

    def test_configuration_errors_do_not_disclose_values(self):
        with self.assertRaises(ValueError) as error:
            targets({**self.targets, "AZURE_CLIENT_ID": "PRIVATE-CANARY"})
        self.assertNotIn("PRIVATE-CANARY", str(error.exception))
        with self.assertRaisesRegex(ValueError, "Missing"):
            targets({})

    def test_placeholders_and_shared_resource_groups_are_rejected(self):
        for key, value in [
            ("AZURE_CLIENT_ID", "00000000-0000-0000-0000-000000000000"),
            ("LAB_RESOURCE_GROUP", "customer-production"),
            ("LAB_RESOURCE_GROUP", self.targets["TF_STATE_RESOURCE_GROUP"]),
        ]:
            with self.subTest(key=key), self.assertRaises(ValueError):
                targets({**self.targets, key: value})

    def test_expired_scope_and_invalid_budgets_are_rejected(self):
        for key, value in [
            ("LAB_EXPIRES_ON", "2000-01-01"),
            ("AZURE_MONTHLY_BUDGET", "NaN"),
            ("AZURE_MONTHLY_BUDGET", "-1"),
        ]:
            with self.subTest(key=key), self.assertRaises(ValueError):
                targets({**self.targets, key: value})
        targets(self.targets)

    def test_matching_plan_can_be_applied_without_exposing_values(self):
        result = review(self.plan, self.source)
        self.assertNotIn("PRIVATE-CANARY", json.dumps(result))
        review(self.plan, self.source, "apply", result["plan_sha256"])

    def test_timestamps_do_not_break_plan_review(self):
        result = review(self.plan, self.source)
        review(
            {**self.plan, "timestamp": "two"},
            self.source,
            "apply",
            result["plan_sha256"],
        )

    def test_source_state_or_resource_changes_invalidate_review(self):
        expected = review(self.plan, self.source)["plan_sha256"]
        for key, value in [
            ("prior_state", {"serial": 2}),
            ("variables", {"location": "changed"}),
            ("configuration", {"changed": True}),
        ]:
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, "changed"):
                review({**self.plan, key: value}, self.source, "apply", expected)
        with self.assertRaises(ValueError):
            review(self.plan, "b" * 40, "apply", expected)

    def test_destroy_replacement_and_scope_expansion_are_rejected(self):
        for actions in [["delete"], ["delete", "create"]]:
            plan = copy.deepcopy(self.plan)
            plan["resource_changes"][0]["change"]["actions"] = actions
            with self.assertRaises(ValueError):
                review(plan, self.source)
        plan = copy.deepcopy(self.plan)
        plan["resource_changes"][0]["address"] = "azurerm_kubernetes_cluster.unapproved"
        with self.assertRaises(ValueError):
            review(plan, self.source)


if __name__ == "__main__":
    unittest.main()
