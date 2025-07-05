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
}
