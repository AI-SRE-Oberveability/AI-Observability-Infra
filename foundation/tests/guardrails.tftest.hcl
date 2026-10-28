mock_provider "azurerm" {}

variables {
  subscription_id     = "11111111-1111-4111-8111-111111111111"
  tenant_id           = "22222222-2222-4222-8222-222222222222"
  resource_group_name = "rg-ai-sre-synthetic"
  location            = "syntheticregion"
  expires_on          = "2099-01-01"
}

run "reject_unrelated_resource_group" {
  command = plan
  variables {
    resource_group_name = "production-existing"
  }
  expect_failures = [var.resource_group_name]
}

run "reject_invalid_expiry" {
  command = plan
  variables {
    expires_on = "not-a-date"
  }
  expect_failures = [var.expires_on]
}
