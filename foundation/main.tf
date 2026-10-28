provider "azurerm" {
  subscription_id                 = var.subscription_id
  tenant_id                       = var.tenant_id
  resource_provider_registrations = "none"

  features {
    resource_group {
      prevent_deletion_if_contains_resources = true
    }
  }
}

resource "azurerm_resource_group" "lab" {
  name     = var.resource_group_name
  location = var.location
  tags = {
    project     = "ai-sre-observability"
    environment = "personal-lab"
    owner       = "javedkumail"
    managed_by  = "terraform"
    expires_on  = var.expires_on
  }

  lifecycle {
    prevent_destroy = true
  }
}

output "resource_group_id" {
  description = "Dedicated lab foundation; application resources are not yet provisioned."
  value       = azurerm_resource_group.lab.id
}
