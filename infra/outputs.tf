output "api_url" {
  description = "Base URL of the API Gateway endpoint"
  value       = aws_apigatewayv2_api.planner.api_endpoint
}

output "lambda_function_name" {
  description = "Name of the deployed Lambda function"
  value       = aws_lambda_function.planner.function_name
}
