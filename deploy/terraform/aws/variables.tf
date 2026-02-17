variable "aws_region" {
  description = "AWS region for deployment"
  type        = string
  default     = "us-east-1"
}

variable "project_name" {
  description = "Project/service name prefix"
  type        = string
  default     = "provenance"
}

variable "environment" {
  description = "Deployment environment"
  type        = string
  default     = "prod"
}

variable "api_image" {
  description = "Container image URI for provenance-api"
  type        = string
}

variable "worker_image" {
  description = "Container image URI for provenance-worker"
  type        = string
}

variable "api_port" {
  description = "API container port"
  type        = number
  default     = 8000
}

variable "api_desired_count" {
  description = "Desired task count for API service"
  type        = number
  default     = 2
}

variable "worker_desired_count" {
  description = "Desired task count for worker service"
  type        = number
  default     = 1
}

variable "api_cpu" {
  description = "Fargate CPU units for API task"
  type        = number
  default     = 512
}

variable "api_memory" {
  description = "Fargate memory (MiB) for API task"
  type        = number
  default     = 1024
}

variable "worker_cpu" {
  description = "Fargate CPU units for worker task"
  type        = number
  default     = 512
}

variable "worker_memory" {
  description = "Fargate memory (MiB) for worker task"
  type        = number
  default     = 1024
}

variable "db_instance_class" {
  description = "RDS instance class"
  type        = string
  default     = "db.t3.micro"
}

variable "db_allocated_storage" {
  description = "RDS allocated storage in GB"
  type        = number
  default     = 20
}

variable "db_name" {
  description = "Database name"
  type        = string
  default     = "provenance"
}

variable "db_username" {
  description = "Database master username"
  type        = string
  default     = "provenance"
}

variable "db_password" {
  description = "Database master password"
  type        = string
  sensitive   = true
}

variable "x_bearer_token" {
  description = "X API bearer token for collection workflows"
  type        = string
  sensitive   = true
  default     = ""
}

variable "webhook_secret" {
  description = "Webhook signing secret"
  type        = string
  sensitive   = true
  default     = ""
}

variable "api_keys" {
  description = "Comma-separated API keys for protected endpoints"
  type        = string
  sensitive   = true
  default     = ""
}

variable "tags" {
  description = "Extra tags applied to resources"
  type        = map(string)
  default     = {}
}
