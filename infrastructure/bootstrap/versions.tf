terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.60"
    }
  }

  backend "s3" {
    bucket         = "sequencer-tf-state-893061519791"
    key            = "bootstrap/terraform.tfstate"
    region         = "us-east-1"
    profile        = "sequencer-mgmt"
    dynamodb_table = "sequencer-tf-locks"
    encrypt        = true
  }
}
