terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

variable "cluster_name" {}
variable "cluster_role_arn" {}
variable "subnet_ids" { type = list(string) }

resource "aws_eks_cluster" "this" {
  name     = var.cluster_name
  role_arn = var.cluster_role_arn
  enabled_cluster_log_types = ["api", "audit", "authenticator"]
  vpc_config {
    subnet_ids = var.subnet_ids
    endpoint_private_access = true
    endpoint_public_access = false
  }
}
