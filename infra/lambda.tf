module "lambda" {
  source  = "terraform-aws-modules/lambda/aws"
  version = "~> 8.8"

  function_name = "school-planner-generate-${var.environment}"
  description   = "Generates weekly planner PDFs from Blackbaud ICS feeds"
  handler       = "handler.handler"
  runtime       = "python3.14"
  timeout       = 30
  memory_size   = 512

  # Package the lambda source + pip dependencies automatically
  source_path = [
    {
      path             = "${path.module}/../lambda"
      pip_requirements = "${path.module}/../lambda/requirements.txt"
      patterns         = ["!tests/.*", "!__pycache__/.*"]
    }
  ]

  # No CloudWatch Logs — privacy hard requirement.
  # The ICS URL and schedule data must never appear in any log.
  attach_cloudwatch_logs_policy           = false
  cloudwatch_logs_retention_in_days       = null
  create_current_version_allowed_triggers = false

  environment_variables = {
    ENVIRONMENT = var.environment
  }

  allowed_triggers = {
    apigw = {
      service    = "apigateway"
      source_arn = "${aws_apigatewayv2_api.planner.execution_arn}/*/*"
    }
  }

  tags = {
    Privacy = "zero-retention"
  }
}
