variable "subscription_id" {
  description = "Exact confirmed personal Azure subscription; supplied outside Git."
  type        = string
  validation {
    condition     = can(regex("^[0-9a-fA-F-]{36}$", var.subscription_id))
    error_message = "A confirmed subscription UUID is required."
  }
}

variable "tenant_id" {
  description = "Exact confirmed personal Entra tenant; supplied outside Git."
  type        = string
  validation {
    condition     = can(regex("^[0-9a-fA-F-]{36}$", var.tenant_id))
    error_message = "A confirmed tenant UUID is required."
  }
}

variable "resource_group_name" {
  description = "Dedicated lab resource group with the agreed rg-ai-sre- prefix."
  type        = string
  validation {
    condition     = can(regex("^rg-ai-sre-[a-z0-9][a-z0-9-]{1,40}$", var.resource_group_name))
    error_message = "Use a dedicated resource group starting with rg-ai-sre-."
  }
}

variable "location" {
  description = "User-confirmed Azure region; there is no default region."
  type        = string
  validation {
    condition     = can(regex("^[a-z][a-z0-9]+$", var.location))
    error_message = "Supply the confirmed Azure region name."
  }
}

variable "expires_on" {
  description = "Explicit lab review/expiry date, YYYY-MM-DD; a tag is not automatic deletion."
  type        = string
  validation {
    condition     = can(formatdate("YYYY-MM-DD", "${var.expires_on}T00:00:00Z"))
    error_message = "Supply a real date in YYYY-MM-DD format."
  }
}
