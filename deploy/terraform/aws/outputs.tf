output "alb_dns_name" {
  description = "Public DNS name of API load balancer"
  value       = aws_lb.api.dns_name
}

output "api_base_url" {
  description = "Base URL for provenance-api"
  value       = "http://${aws_lb.api.dns_name}"
}

output "ecs_cluster_name" {
  description = "ECS cluster name"
  value       = aws_ecs_cluster.main.name
}

output "rds_endpoint" {
  description = "RDS endpoint address"
  value       = aws_db_instance.postgres.address
}

output "ecr_api_repository_url" {
  description = "ECR repository URL for API image"
  value       = aws_ecr_repository.api.repository_url
}

output "ecr_worker_repository_url" {
  description = "ECR repository URL for worker image"
  value       = aws_ecr_repository.worker.repository_url
}
