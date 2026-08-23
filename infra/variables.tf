variable "aws_region" {
  description = "AWS region for all resources"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Deployment environment (e.g. prod, staging)"
  type        = string
  default     = "prod"
}

variable "frontend_origin" {
  description = "GitHub Pages origin URL for CORS (no trailing slash)"
  type        = string
  # TODO: Replace with actual GitHub Pages URL once known
  default = "https://YOUR_ORG.github.io"
}

variable "lambda_zip_path" {
  description = "Path to the packaged Lambda zip file"
  type        = string
  default     = "../lambda/package.zip"
}
