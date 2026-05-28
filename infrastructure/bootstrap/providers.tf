provider "aws" {
  region  = "us-east-1"
  profile = "sequencer-mgmt"
  alias   = "orchestrator"

  assume_role {
    role_arn     = "arn:aws:iam::${aws_organizations_account.orchestrator.id}:role/OrganizationAccountAccessRole"
    session_name = "TerraformOrchestratorSession"
  }
}

provider "aws" {
  region  = "us-east-1"
  profile = "sequencer-mgmt"
  alias   = "manufacturing"

  assume_role {
    role_arn     = "arn:aws:iam::${aws_organizations_account.manufacturing.id}:role/OrganizationAccountAccessRole"
    session_name = "TerraformManufacturingSession"
  }
}

provider "aws" {
  region  = "us-east-1"
  profile = "sequencer-mgmt"
  alias   = "logistics"

  assume_role {
    role_arn     = "arn:aws:iam::${aws_organizations_account.logistics.id}:role/OrganizationAccountAccessRole"
    session_name = "TerraformLogisticsSession"
  }
}

provider "aws" {
  region  = "us-east-1"
  profile = "sequencer-mgmt"
  alias   = "clinical"

  assume_role {
    role_arn     = "arn:aws:iam::${aws_organizations_account.clinical.id}:role/OrganizationAccountAccessRole"
    session_name = "TerraformClinicalSession"
  }
}

provider "aws" {
  region  = "us-east-1"
  profile = "sequencer-mgmt"
  alias   = "qc_lab"

  assume_role {
    role_arn     = "arn:aws:iam::${aws_organizations_account.qc_lab.id}:role/OrganizationAccountAccessRole"
    session_name = "TerraformQCLabSession"
  }
}