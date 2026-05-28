variable "account_label" {
  type        = string
  description = "Short label for this account (orchestrator, manufacturing, etc.) — used in resource descriptions"
}

variable "github_repo" {
  type        = string
  description = "GitHub repo in OWNER/REPO format, e.g. ITSMEsouptik/Sequencer-Orchestrator"
}

variable "oidc_thumbprint" {
  type        = string
  description = "SHA-1 thumbprint of the GitHub OIDC provider's TLS cert"
  default     = "6938fd4d98bab03faadb97b34396831e3780aea1"
}
