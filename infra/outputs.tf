output "api_url" {
  description = "Base URL of the API Gateway endpoint"
  value       = aws_apigatewayv2_api.planner.api_endpoint
}

output "lambda_function_name" {
  description = "Name of the deployed Lambda function"
  value       = module.lambda.lambda_function_name
}

output "lambda_function_arn" {
  description = "ARN of the deployed Lambda function"
  value       = module.lambda.lambda_function_arn
}
