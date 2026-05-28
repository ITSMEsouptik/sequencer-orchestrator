# ─────────────────────────────────────────────────────────────
# SHARED TRUST POLICY
# Allows the management account root to assume TerraformExecutionRole
# in any child account. Using account root (not a specific IAM user)
# means any future IAM Identity Center principal with sts:AssumeRole
# permission can use these roles — no role updates needed when team
# members are added or removed.
# ─────────────────────────────────────────────────────────────
locals {
  terraform_role_trust_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          AWS = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:root"
        }
        Action = "sts:AssumeRole"
      }
    ]
  })
}

# ─────────────────────────────────────────────────────────────
# ORCHESTRATOR ACCOUNT — TerraformExecutionRole
# Created in the orchestrator account via provider alias.
# AdministratorAccess is intentional at bootstrap stage — will be
# scoped down to least-privilege once the account's resource
# inventory is stable.
# ─────────────────────────────────────────────────────────────
resource "aws_iam_role" "terraform_orchestrator" {
  provider           = aws.orchestrator
  name               = "TerraformExecutionRole"
  assume_role_policy = local.terraform_role_trust_policy
  description        = "Role for Terraform to manage resources in the Orchestrator account"
}

resource "aws_iam_role_policy_attachment" "terraform_orchestrator_admin" {
  provider   = aws.orchestrator
  role       = aws_iam_role.terraform_orchestrator.name
  policy_arn = "arn:aws:iam::aws:policy/AdministratorAccess"
}

output "terraform_orchestrator_role_arn" {
  value       = aws_iam_role.terraform_orchestrator.arn
  description = "ARN of the IAM role for Terraform in the Orchestrator account"
}

# ─────────────────────────────────────────────────────────────
# MANUFACTURING ACCOUNT — TerraformExecutionRole
# Created in the manufacturing account via provider alias.
# Same role name across all accounts so cross-account automation
# scripts can use a predictable ARN pattern:
#   arn:aws:iam::<account-id>:role/TerraformExecutionRole
# ─────────────────────────────────────────────────────────────
resource "aws_iam_role" "terraform_manufacturing" {
  provider           = aws.manufacturing
  name               = "TerraformExecutionRole"
  assume_role_policy = local.terraform_role_trust_policy
  description        = "Role for Terraform to manage resources in the Manufacturing account"
}

resource "aws_iam_role_policy_attachment" "terraform_manufacturing_admin" {
  provider   = aws.manufacturing
  role       = aws_iam_role.terraform_manufacturing.name
  policy_arn = "arn:aws:iam::aws:policy/AdministratorAccess"
}

output "terraform_manufacturing_role_arn" {
  value       = aws_iam_role.terraform_manufacturing.arn
  description = "ARN of the IAM role for Terraform in the Manufacturing account"
}

# ─────────────────────────────────────────────────────────────
# LOGISTICS ACCOUNT — TerraformExecutionRole
# ─────────────────────────────────────────────────────────────
resource "aws_iam_role" "terraform_logistics" {
  provider           = aws.logistics
  name               = "TerraformExecutionRole"
  assume_role_policy = local.terraform_role_trust_policy
  description        = "Role for Terraform to manage resources in the Logistics account"
}

resource "aws_iam_role_policy_attachment" "terraform_logistics_admin" {
  provider   = aws.logistics
  role       = aws_iam_role.terraform_logistics.name
  policy_arn = "arn:aws:iam::aws:policy/AdministratorAccess"
}

output "terraform_logistics_role_arn" {
  value       = aws_iam_role.terraform_logistics.arn
  description = "ARN of the IAM role for Terraform in the Logistics account"
}

# ─────────────────────────────────────────────────────────────
# CLINICAL ACCOUNT — TerraformExecutionRole
# Clinical account will likely require tighter SCPs (HIPAA-adjacent
# data handling). AdministratorAccess here is temporary — will be
# replaced with a scoped policy before any PHI workloads land.
# ─────────────────────────────────────────────────────────────
resource "aws_iam_role" "terraform_clinical" {
  provider           = aws.clinical
  name               = "TerraformExecutionRole"
  assume_role_policy = local.terraform_role_trust_policy
  description        = "Role for Terraform to manage resources in the Clinical account"
}

resource "aws_iam_role_policy_attachment" "terraform_clinical_admin" {
  provider   = aws.clinical
  role       = aws_iam_role.terraform_clinical.name
  policy_arn = "arn:aws:iam::aws:policy/AdministratorAccess"
}

output "terraform_clinical_role_arn" {
  value       = aws_iam_role.terraform_clinical.arn
  description = "ARN of the IAM role for Terraform in the Clinical account"
}

# ─────────────────────────────────────────────────────────────
# QC LAB ACCOUNT — TerraformExecutionRole
# ─────────────────────────────────────────────────────────────
resource "aws_iam_role" "terraform_qc_lab" {
  provider           = aws.qc_lab
  name               = "TerraformExecutionRole"
  assume_role_policy = local.terraform_role_trust_policy
  description        = "Role for Terraform to manage resources in the QC Lab account"
}

resource "aws_iam_role_policy_attachment" "terraform_qc_lab_admin" {
  provider   = aws.qc_lab
  role       = aws_iam_role.terraform_qc_lab.name
  policy_arn = "arn:aws:iam::aws:policy/AdministratorAccess"
}

output "terraform_qc_lab_role_arn" {
  value       = aws_iam_role.terraform_qc_lab.arn
  description = "ARN of the IAM role for Terraform in the QC Lab account"
}