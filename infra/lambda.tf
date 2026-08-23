# IAM role for the Lambda function
resource "aws_iam_role" "lambda_exec" {
  name = "school-planner-lambda-${var.environment}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })
}

# Minimal permissions — only what's needed.
# NO CloudWatch Logs permissions. This is intentional.
# The Lambda has no business writing logs that could contain schedule data.
# If you need operational visibility, add ONLY metrics (not log content).
resource "aws_iam_role_policy" "lambda_minimal" {
  name = "school-planner-lambda-minimal"
  role = aws_iam_role.lambda_exec.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        # Allow CloudWatch metrics only (for invocation counts, errors, duration)
        # Explicitly NOT granting logs:CreateLogGroup, logs:CreateLogStream, logs:PutLogEvents
        Effect = "Allow"
        Action = [
          "cloudwatch:PutMetricData"
        ]
        Resource = "*"
        Condition = {
          StringEquals = {
            "cloudwatch:namespace" = "AWS/Lambda"
          }
        }
      }
    ]
  })
}

# Lambda function
resource "aws_lambda_function" "planner" {
  function_name = "school-planner-generate-${var.environment}"
  role          = aws_iam_role.lambda_exec.arn
  handler       = "handler.handler"
  runtime       = "python3.14"
  timeout       = 30
  memory_size   = 512

  filename         = var.lambda_zip_path
  source_code_hash = filebase64sha256(var.lambda_zip_path)

  environment {
    variables = {
      # No secrets needed — ICS feeds are unauthenticated.
      # This block exists as a placeholder if anything is needed later.
      ENVIRONMENT = var.environment
    }
  }
}

# Lambda permission for API Gateway to invoke
resource "aws_lambda_permission" "apigw" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.planner.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.planner.execution_arn}/*/*"
}
