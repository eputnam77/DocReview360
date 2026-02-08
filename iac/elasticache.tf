terraform {
  required_providers {
    aws = {
      source = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

variable "cluster_id" {}
variable "auth_token" {
  type      = string
  sensitive = true
  default   = null
}

resource "aws_elasticache_replication_group" "this" {
  replication_group_id       = var.cluster_id
  description                = "DocReview360 Redis cache"
  engine                     = "redis"
  engine_version             = "7.0"
  node_type                  = "cache.t3.micro"
  parameter_group_name       = "default.redis7"
  num_cache_clusters         = 1
  automatic_failover_enabled = false
  multi_az_enabled           = false
  transit_encryption_enabled = true
  at_rest_encryption_enabled = true
  auth_token                 = var.auth_token
  snapshot_retention_limit   = 7
  apply_immediately          = true
}
