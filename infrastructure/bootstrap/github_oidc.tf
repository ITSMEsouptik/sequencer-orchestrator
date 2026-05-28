module "github_oidc_management" {
  source        = "./modules/github_oidc_role"
  providers     = { aws = aws }
  account_label = "management"
  github_repo   = "ITSMEsouptik/sequencer-platform"
}


module "github_oidc_orchestrator" {
  source = "./modules/github_oidc_role"
  providers = {
    aws = aws.orchestrator
  }
  account_label = "orchestrator"
  github_repo   = "ITSMEsouptik/sequencer-orchestrator"
}

module "github_oidc_manufacturing" {
  source        = "./modules/github_oidc_role"
  providers     = { aws = aws.manufacturing }
  account_label = "manufacturing"
  github_repo   = "ITSMEsouptik/sequencer-manufacturing-vendor"
}

module "github_oidc_logistics" {
  source        = "./modules/github_oidc_role"
  providers     = { aws = aws.logistics }
  account_label = "logistics"
  github_repo   = "ITSMEsouptik/sequencer-logistics-vendor"
}

module "github_oidc_clinical" {
  source        = "./modules/github_oidc_role"
  providers     = { aws = aws.clinical }
  account_label = "clinical"
  github_repo   = "ITSMEsouptik/sequencer-clinical-vendor"
}

module "github_oidc_qc_lab" {
  source        = "./modules/github_oidc_role"
  providers     = { aws = aws.qc_lab }
  account_label = "qc_lab"
  github_repo   = "ITSMEsouptik/sequencer-qc-lab-vendor"
}


output "github_actions_role_arns" {
  value = {
    orchestrator  = module.github_oidc_orchestrator.github_actions_role_arn
    manufacturing = module.github_oidc_manufacturing.github_actions_role_arn
    logistics     = module.github_oidc_logistics.github_actions_role_arn
    clinical      = module.github_oidc_clinical.github_actions_role_arn
    qc_lab        = module.github_oidc_qc_lab.github_actions_role_arn
    management    = module.github_oidc_management.github_actions_role_arn
  }
  description = "GitHubActionsRole ARNs by account"
}

