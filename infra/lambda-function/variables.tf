variable "context" {
  description = <<EOF
Information about the context in which the service is being used.
environment_name - Unique environment name to use for namespacing this resource.
environment_type - The type of environment, i.e. a designation of the reason for the service's deployment.
product_name - The main product this supports.
feature_name - High-level feature name to which this set of resources belong. Useful for tracking cost and ownership.
team_name - The engineering team responsible for maintaining the service.
EOF
  type = object({ 
    environment_name=string,
    environment_type=string,
    product_name=string,
    feature_name=string,
    team_name=string
  })
}

variable "base_function_name" {
  description = "The base name of the function, without namespacing by environment"
  type = string
}

variable "description" {
  description = "A human-readable description of the function"
  type = string
}

variable "runtime" {
  description = "Code runtime for the function"
  type = string
  default = "python3.8"
}

variable "entry_point" {
  description = "Python symbol used for the lambda function entry point.  Typically `src.adapters.aws_lambda.<your-function>`."
  type = string
}

variable "memory" {
  description = "Memory setting for the lambda, which also controls CPU"
  type = number
  default = 128
}

variable "timeout" {
  description = "Timeout, in seconds, for the lambda.  Max 900 second (15 min)"
  type = number
  default = 3
}

variable "max_concurrency" {
  description = "The maximum number of concurrent instances of this lambda to run, up to the account maximum. 0 prevents all execution, -1 yields umlimited concurrency."
  type = number
  default = -1
}

variable "provisioned_concurrency" {
  description = "If not null, specifies the provisioned concurrency (warm instances) to maintain at any given time."
  type = number
  default = null
}

variable "lambda_policy_document" {
  description = "An IAM policy document (JSON) for the lambda's role.  Should include cloudwatch logging at a minimum."
  type = string
}

variable "environment_variables" {
  description = "A map of environment variables to be injected into the lambda function.  Be aware that there is a 4KB limit on variables."
  type = map
  default = null
}

variable "layers" {
  description = "A list of layer ARNs to use with the function. The AWS limit is 5."
  type = list(string)
  default = []
}

variable "datadog_log_ingestor" {
  description = "ARN of a lambda function that will ingest cloudwatch logs for DataDog."
  type = string
  default = ""
}

variable "code_zip" {
  description = "Path to a zip archive containing source code to send to AWS."
  type = string
}
