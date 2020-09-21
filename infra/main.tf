terraform {
  required_version = ">= 0.12, < 0.13"
}

provider "aws" {
  region = "us-east-1"
  # Allow any 3.x version of the AWS provider
  version = "~> 3.0"
  profile = "dev_us-east-1"
}

terraform {
  backend "s3" {
    bucket = "ngtdevel-terraform-states-us-east-1"
    key = "bqp-temp-testing/terraform.tfstate"
    region = "us-east-1"
    profile = "dev_us-east-1"
    encrypt = true
  }
}

data "template_file" "safety_scan_complete_lambda_policy" {
  template = file("${path.module}/templates/test-lambda.json")
  vars = {}
}

module "test_function" {
  source = "./lambda-function"
  context = local.context
  base_function_name = "test-s3-issue-function"
  description = "Temp function used for reproducing the S3 issue for which we have opened a support ticket"
  entry_point = "src.lambda.run_locust_test"
  lambda_policy_document = data.template_file.safety_scan_complete_lambda_policy.rendered
  memory = 2048
  timeout = 120
  code_zip = "${path.cwd}/.test.zip"
}
