variable "aws_region" {
  description = "AWS region for all resources"
  type        = string
  default     = "us-east-2"
}

variable "environment" {
  description = "Deployment environment (e.g. prod, staging)"
  type        = string
  default     = "prod"
}

variable "frontend_origin" {
  description = "GitHub Pages origin URL for CORS (no trailing slash)"
  type        = string
  default     = "https://seantibor.github.io"
}
