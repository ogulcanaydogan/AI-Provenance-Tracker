# AWS Terraform Deployment (ECS + RDS + ALB + ECR)

This stack provisions:
- `provenance-api` on ECS Fargate behind ALB
- `provenance-worker` on ECS Fargate
- Postgres on RDS
- ECR repos for API/worker images
- VPC, subnets, security groups, CloudWatch log groups

## Quick Start

1. Copy vars file:
```bash
cd deploy/terraform/aws
cp terraform.tfvars.example terraform.tfvars
```

2. Set image URIs and database password in `terraform.tfvars`.

3. Initialize and apply:
```bash
terraform init
terraform plan
terraform apply
```

4. Use output URL:
```bash
terraform output api_base_url
```

## Notes
- API runs with `RUN_SCHEDULER_IN_API=false`.
- Worker runs with scheduler enabled (`SCHEDULER_ENABLED=true`).
- For production hardening, add TLS (ACM), WAF, private ECS subnets + NAT, and Secrets Manager/SSM.
