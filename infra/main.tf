terraform {
  required_version = ">= 1.5"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  # Remote state — configure bucket/key via backend config or CI env vars
  backend "s3" {}
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "school-planner"
      ManagedBy   = "terraform"
      Environment = var.environment
    }
  }
}
