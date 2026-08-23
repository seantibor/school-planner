# HTTP API (v2) — lightweight, cheaper than REST API for this use case
resource "aws_apigatewayv2_api" "planner" {
  name          = "school-planner-${var.environment}"
  protocol_type = "HTTP"

  cors_configuration {
    allow_origins = [var.frontend_origin]
    allow_methods = ["POST", "OPTIONS"]
    allow_headers = ["Content-Type"]
    max_age       = 3600
  }
}

# Integration with Lambda
resource "aws_apigatewayv2_integration" "lambda" {
  api_id                 = aws_apigatewayv2_api.planner.id
  integration_type       = "AWS_PROXY"
  integration_uri        = module.lambda.lambda_function_invoke_arn
  payload_format_version = "2.0"
}

# POST /generate route
resource "aws_apigatewayv2_route" "generate" {
  api_id    = aws_apigatewayv2_api.planner.id
  route_key = "POST /generate"
  target    = "integrations/${aws_apigatewayv2_integration.lambda.id}"
}

# Default stage with auto-deploy
# IMPORTANT: Access logging is explicitly NOT configured.
# This is a hard privacy requirement — request bodies (containing ICS URLs)
# must never appear in any log.
resource "aws_apigatewayv2_stage" "default" {
  api_id      = aws_apigatewayv2_api.planner.id
  name        = "$default"
  auto_deploy = true

  # No access_log_settings block — this is intentional, not an oversight.
  # Do NOT add logging here without reviewing the privacy requirements.

  default_route_settings {
    throttling_burst_limit = 10
    throttling_rate_limit  = 5
  }
}
