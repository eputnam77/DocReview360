terraform {
  required_providers {
    aws = {
      source = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

variable "db_name" {}

resource "aws_db_instance" "this" {
  identifier = var.db_name
  engine     = "postgres"
  instance_class = "db.t3.micro"
  allocated_storage = 20
  storage_encrypted = true
  publicly_accessible = false
  backup_retention_period = 7
  deletion_protection = true
  auto_minor_version_upgrade = true
}
