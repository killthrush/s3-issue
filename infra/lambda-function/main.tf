terraform {
  required_version = ">= 0.12, < 0.13"
}

data "template_file" "assume_role_policy" {
  template = file("${path.module}/templates/assume-role-policy.json")
}

resource "aws_lambda_function" "function" {
  function_name = local.function_name
  role = aws_iam_role.lambda_role.arn
  filename = var.code_zip
  source_code_hash = filebase64sha256(var.code_zip)
  handler = var.entry_point
  runtime = var.runtime
  layers = var.layers
  publish = var.provisioned_concurrency == null ? false : true
  memory_size = var.memory
  timeout = var.timeout
  reserved_concurrent_executions = var.max_concurrency
  tags = {
    "ngt:name" = local.function_name
    "ngt:environment_name" = var.context.environment_name
    "ngt:environment_type" = var.context.environment_type
    "ngt:product" = var.context.product_name
    "ngt:feature" = var.context.feature_name
    "ngt:team" = var.context.team_name
  }
  dynamic "environment" {
    for_each = var.environment_variables == null ? [] : [var.environment_variables]
    content {
      variables = environment.value
    }
  }
}

resource "aws_cloudwatch_log_group" "lambda_log_group" {
  name = "/aws/lambda/${aws_lambda_function.function.function_name}"
  retention_in_days = 14
}

# This is currently disabled due to a bug in terraform:
# https://github.com/terraform-providers/terraform-provider-aws/issues/12923
resource "aws_lambda_provisioned_concurrency_config" "function_concurrency" {
  count = var.provisioned_concurrency == null ? 0 : 0
  function_name = aws_lambda_function.function.arn
  provisioned_concurrent_executions = var.provisioned_concurrency
  qualifier = aws_lambda_function.function.version
}

# This is currently disabled, as our datadog setup creates the subscription automatically.
# If this fails for some reason, this is how you'd do it manually.
resource "aws_cloudwatch_log_subscription_filter" "datadog_log_ingest" {
  count = var.datadog_log_ingestor == "" ? 0 : 0
  name = "${local.function_name}-dd-log-ingest"
  log_group_name = "/aws/lambda/${aws_lambda_function.function.function_name}"
  filter_pattern = ""
  destination_arn = var.datadog_log_ingestor
}

resource "aws_iam_policy" "function_policy" {
  name = "${local.function_name}-role-policy"
  path = "/"
  description = "Lambda policy for ${local.function_name}"
  policy = var.lambda_policy_document
}

resource "aws_iam_role_policy_attachment" "lambda_role_policy_attachment" {
  role = aws_iam_role.lambda_role.name
  policy_arn = aws_iam_policy.function_policy.arn
}

resource "aws_iam_role" "lambda_role" {
  name = "${local.function_name}-role"
  assume_role_policy = data.template_file.assume_role_policy.rendered
  tags = {
    "ngt:name" = "${local.function_name}-role"
    "ngt:environment_name" = var.context.environment_name
    "ngt:environment_type" = var.context.environment_type
    "ngt:product" = var.context.product_name
    "ngt:feature" = var.context.feature_name
    "ngt:team" = var.context.team_name
  }
}