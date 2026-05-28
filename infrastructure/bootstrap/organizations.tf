# ─────────────────────────────────────────────────────────────
# ORCHESTRATOR ACCOUNT
# Saga coordinator — owns workflow state, drives all domain
# accounts via SQS/SNS. Hub of the hub-and-spoke topology.
# ─────────────────────────────────────────────────────────────
resource "aws_organizations_account" "orchestrator" {
  name      = "sequencer-orchestrator"
  email     = "mandalsouptik1998+orchestrator@gmail.com"
  role_name = "OrganizationAccountAccessRole"

  lifecycle {
    prevent_destroy = true
  }
}

output "account_id_orchestrator" {
  value       = aws_organizations_account.orchestrator.id
  description = "AWS Account ID for the Orchestrator account."
}

# ─────────────────────────────────────────────────────────────
# MANUFACTURING ACCOUNT
# CAR-T manufacturing facility systems. Consumes slot-request
# events from the orchestrator and publishes completion events.
# ─────────────────────────────────────────────────────────────
resource "aws_organizations_account" "manufacturing" {
  name      = "sequencer-manufacturing"
  email     = "mandalsouptik1998+manufacturing@gmail.com"
  role_name = "OrganizationAccountAccessRole"

  lifecycle {
    prevent_destroy = true
  }
}

output "account_id_manufacturing" {
  value       = aws_organizations_account.manufacturing.id
  description = "AWS Account ID for the Manufacturing account."
}

# ─────────────────────────────────────────────────────────────
# LOGISTICS ACCOUNT
# Chain-of-custody, courier coordination, and cold-chain
# monitoring for apheresis and infusion product transit.
# ─────────────────────────────────────────────────────────────
resource "aws_organizations_account" "logistics" {
  name      = "sequencer-logistics"
  email     = "mandalsouptik1998+logistics@gmail.com"
  role_name = "OrganizationAccountAccessRole"

  lifecycle {
    prevent_destroy = true
  }
}

output "account_id_logistics" {
  value       = aws_organizations_account.logistics.id
  description = "AWS Account ID for the Logistics account."
}

# ─────────────────────────────────────────────────────────────
# CLINICAL ACCOUNT
# Hospital and treatment centre systems. Receives infusion-ready
# notifications and publishes post-infusion monitoring events.
# ─────────────────────────────────────────────────────────────
resource "aws_organizations_account" "clinical" {
  name      = "sequencer-clinical"
  email     = "mandalsouptik1998+clinical@gmail.com"
  role_name = "OrganizationAccountAccessRole"

  lifecycle {
    prevent_destroy = true
  }
}

output "account_id_clinical" {
  value       = aws_organizations_account.clinical.id
  description = "AWS Account ID for the Clinical account."
}

# ─────────────────────────────────────────────────────────────
# QC LAB ACCOUNT
# Quality control and product release testing. Publishes
# QC_PASSED / QC_HOLD events that gate the release step.
# ─────────────────────────────────────────────────────────────
resource "aws_organizations_account" "qc_lab" {
  name      = "sequencer-qc-lab"
  email     = "mandalsouptik1998+qc-lab@gmail.com"
  role_name = "OrganizationAccountAccessRole"

  lifecycle {
    prevent_destroy = true
  }
}

output "account_id_qc_lab" {
  value       = aws_organizations_account.qc_lab.id
  description = "AWS Account ID for the QC Lab account."
}