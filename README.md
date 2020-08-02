# Overview

This repository contains the code and infrastructure configuration needed to maintain Numerated's Document Storage service.  This is a cloud-native serverless architecture that manages the storage, security, safety, and accessibility of documents used for various SMB loan products.

# Getting Started

This project requires a full installation of the developer tools found [here](https://github.com/easternlabs/developer-setup); this allows us to keep the instructions here short and sweet.  This includes the base installs, devops tools, python tools, and AWS tools.  The code in this repo is designed so you can do a lot of work without a deployment, but when you do need to deploy, it's quick and simple.

## Step 1 - Python environment

This project uses python 3.8.2, so you should probably start by configuring pyenv for the project:
```bash
pyenv local 3.8.2
```
Next, create a virtualenv using your choice of tool (virtualenv shown):
```bash
virtualenv -p $(pyenv which python) venv
source venv/bin/activate
```

Lastly, install python dependencies:
```bash
pip install -r requirements-dev.txt
```

## Step 2 - Running tools

To make your code look nice and clean:
```bash
# Run flake8 linter
bash cicd/run_linter.sh

# Run black
bash cicd/run_code_cleanup.sh
```

To run tests:
```bash
# Run unit tests only
bash cicd/run_tests.sh unit

# Run integration tests only
bash cicd/run_tests.sh integration

# Run performance tests only
bash cicd/run_tests.sh performance

# Run all unit, performance, and integration tests
bash cicd/run_tests.sh

# Run acceptance tests on your own copy of a real deployed service (see next section for details)
aws-login dev_us-east-1
bash cicd/run_acceptance_tests.sh <your-environment>

# Run acceptance tests on dev/catfleet
aws-login dev_us-east-1
bash cicd/run_acceptance_tests.sh dev ngt041m http://tiger-banker.ngtcloud.com
```

Note that some of the more complex tests require additional dependencies to be installed, like `clamav`. If you don't have the dependency, the test will be skipped during the run; just follow the instructions if you would like to include it.


### Logging Config

The default log level is set to `DEBUG`.  To change this when running tests or your IDE, set the `NGT_LOG_LEVEL` environment variable to a value other than "DEBUG".  Development logs are written to the console and are color-coded with the `colorama` library.  AWS Lambda logs JSON records to Amazon CloudWatch.

## Step 3 - Running the service in AWS

First, you'll need to log in through AWS SSO:
```bash
aws-login dev_us-east-1
```

Next, you need to package and deploy your AWS resources and lambda code.  Here's how to do in install from a completely clean repo:
```bash
# Initialize terraform, when starting fresh or changing modules.
# This will create a terraform workspace keyed to your email, and AWS resources will be namespaced accordingly.
# For example ben.peterson@numerated.com translates to an environment_name of `devbenpeterson`.
bash cicd/init.sh <your numerated email>

# Full clean and reinstall.  Will prompt so you can check correctness before deploy.
bash cicd/build_lambda_payload.sh full-rebuild && bash cicd/deploy.sh
```

Here's how to build and redeploy more quickly during development:
```bash
# Quick update to get your changed python files out there.  No confirmation during deploy.
bash cicd/build_lambda_payload.sh && bash cicd/deploy.sh yolo
```

Terraform typically needs to initialize itself by installing modules and loading state.  After cloning the repo or after major changes have been made to the terraform code, you might see an error like the following:
```bash
Error: Module not installed
  on main.tf line 100:
  48: module "my_module" {
This module is not yet installed. Run "terraform init" to install all modules
required by this configuration.
```
Running `terraform init` is necessary as the error message states, however given that terraform is pretty sensitive to working directory, we use a script to do it properly:
```bash
# Re-initialize terraform when making new modules or changing parameters of existing modules.
bash cicd/deploy.sh init
```

Here's a few other tricks:
```bash
# Update dependencies only, no deploy
bash cicd/build_lambda_payload.sh deps-only

# Build and deploy, but confirm first.
bash cicd/build_lambda_payload.sh && bash cicd/deploy.sh

# Just double check the infrastructure state
bash cicd/deploy.sh dryrun

# Totally wipe out your service and start fresh.
# Note that this can take 15-20 minutes because of cloudfront.
bash cicd/teardown.sh
```

IMPORTANT NOTE: that once creating the service for the first time, it will take 15-20 minutes for it to come online.  This is mainly because we use CloudFront; it requires some time to come online.  After all, it's pushing state all over the world!  Most changes you will do as a developer will not require making any changes to cloudfront, and it will be a lot faster (usually less than 10 seconds for a typical code change)


# Project Structure

The overall structure of this project is not arbitrary; it's designed to address several key values:
* Simplicity - relatively flat dependency graph, clear separation of concerns
* Self-documenting - code that aligns with the business domain is front and center, with technology concerns at the periphery. Modules are small and focused.
* Easy to package/deploy/test - we need to be able to do these things, but at low cost
* Multi-modal - we want the ability to execute business commands using different mechanisms; it adds flexibility without adding complexity

The following sections briefly describe the major components of the repository to give guidance on how to organize new code.

## Core Package

This package is the kernel, the implementation of the business domain in code, and is the reason why this service exists.  The main unit of currency is a `command`, a verb in the business domain.  Commands are transactional, simple, and have a well-defined sphere of influence - essentially the fundamental building block of an application.  They also often result in state changes and may emit events - side effects that other parties might be interested in. These modules are primarily used in lambda functions, but they can be fronted by anything.  Events will be published to SNS topics when running in AWS, but could theoretically be published as in-memory messages or callbacks.

Core modules should be self-documenting and clearly describe a business process to the reader.  The tests for these modules should do the same.

## Adapters Package

If the core package represents the domain code, then adapters represent the code that allow one to execute the domain code in different contexts.  For example, these modules can define AWS Lambda function entry points so we can run in the cloud.  Or they could define command-line functions or initialize a python REPL for experimentation.  This adds a great deal of flexibility to our solution without adding a lot of code - it's all about how the code is organized.

## Library Package

Contains non-domain shared code that can be easily unit tested. Only consider putting code in here if it's used in multiple places. If other services have the same library code and it's got a useful, well-defined API we might want to consider extracting the code into a pypi package.

## Tests Package

Contains unit and integration tests for everything under the `src` directory.  Test module structure should match the `src` folder structure exactly - we should be able to easily find tests by visual inspection. Tests should be tagged with `pytest.mark.unit`, `pytest.mark.integration`, or `pytest.mark.performance`; this gives us some control over which things we can easily run during development.

## Acceptance Tests Package

Contains acceptance tests for deployed code.  Unlike unit or integration tests, this requires significant setup work in the form of a deployment to AWS.  As such, these are not intended to run often or gate a PR.  But they should be considered for gating releases and for sanity checking during development. These are tagged in pytest so we don't mix them up.  The folder structure is also different; it does not follow the code but the features of the service.

## CICD

This directory contains scripts used to test, clean, and deploy code to the cloud.  The `terraform` directory is for terraform modules; with an active login session with AWS SSO, you can deploy the entire service (or part of it) to the cloud.  The `datadog` directory is for storing JSON definitions for dashboards and alerts that relate to the service - this provides some level of ownership and change management for these things.

## Docs

This directory contains markdown and other documentation that's tightly coupled to the code in this repository.  This should be supplementary; the code and tests should be as self-documenting as possible.

# API Guide

At present the service supports the storage and retrieval of documents using presigned S3 URLs with very short lifetimes.  A single storage link can support a PUT (upload) of a single file to a secure S3 bucket, and a single retrieval link can support a GET for a single file from S3.  The Command API is a RESTful interface that securely orchestrates this process.  See the Architecture Overview for more details.

## Generate Storage Links v1
To generate a set of presigned storage links, you can POST some specs to the Generate Storage Links endpoint, filling in document, application, and bank IDs where appropriate.  Depending on the task, the document and application IDs may correspond to values that exist in the Platform DB; at present there's no requirement here aside from the values must be UUIDs.  Content types sent with the files will be stored in S3 as object metadata.  You can also specify a timeout in seconds to apply to the links; when the timeout has passed, the user will get a 403 if they attempt to use it.  The X-Signature header should contain an HMAC value, the hash of the payload using a bank-specific shared secret known to both the Platform and AWS.  Requests with an invalid signature will be denied.

NOTE: this version of the API supports the transitional period when the document metadata still lives in the platform database.

```
POST /commands/<bank_id>/generate_storage_links/v1
Accept: application/json
X-Signature: <hash value>
```
```json
{
    "timeout_in_seconds": 100,
    "documents_to_store": [
        {"document_id": "00000000-0000-0000-0000-000000000001", "presentation_filename": "doc1.pdf", "content_type": "application/pdf"},
        {"document_id": "00000000-0000-0000-0000-000000000002", "presentation_filename": "doc2.pdf", "content_type": "application/pdf"},
        {"document_id": "00000000-0000-0000-0000-000000000003", "presentation_filename": "doc3.pdf", "content_type": "application/pdf"}
    ],
    "timestamp": "2020-06-02T12:22:31+00:00",
    "application_id": "00000000-0000-0000-0000-000000000000",
    "bank_id": "<bank_id>>"
}
```


## Generate Retrieval Links v1
To generate a set of presigned retrieval links, you can POST some specs to the Generate Retrieval Links endpoint, filling in document, application, and bank IDs where appropriate.  Depending on the task, the document and application IDs may correspond to values that exist in the Platform DB; at present there's no requirement here aside from the values must be UUIDs.  You can also specify a timeout in seconds to apply to the links; when the timeout has passed, the user will get a 403 if they attempt to use it.  The X-Signature header should contain an HMAC value, the hash of the payload using a bank-specific shared secret known to both the Platform and AWS.  Requests with an invalid signature will be denied.

NOTE: this version of the API supports the transitional period when the document metadata still lives in the platform database.

```
POST /commands/<bank_id>/generate_retrieval_links/v1
Accept: application/json
X-Signature: <hash value>
```
```json
{
    "timeout_in_seconds": 100,
    "requested_documents": [
        {"document_id": "00000000-0000-0000-0000-000000000001", "presentation_filename": "doc1.pdf"},
        {"document_id": "00000000-0000-0000-0000-000000000002", "presentation_filename": "doc2.pdf"},
        {"document_id": "00000000-0000-0000-0000-000000000003", "presentation_filename": "doc3.pdf"}
    ],
    "timestamp": "2020-06-02T12:33:54+00:00",
    "application_id": "00000000-0000-0000-0000-000000000000",
    "bank_id": "<bank_id>>"
}
```


# Prod Support

## Logs

There are several different kinds of logs produced by the service, the two main types being access logs and lambda logs.  The former type will record request traffic while the latter will record the details of what occurs behind the requests.

### Access Logs

* We create a dedicated cloudfront distribution for each for each bank, however access logs for these distributions are stored in a common location - the bucket `<environment>-ds-cf-access-logs-<account id>`.  Each bank has a prefix in this bucket to logs for that bank's distribution. Unfortunately, these logs are not natively portable to cloudwatch or datadog.
* Each document storage bucket also has an access log, organized in a similar manner to that of the cloudfront distributions - all logs are stored together in the same bucket but prefixed by bank ID.  These logs are in the bucket `<environment>-ds-s3-access-logs-<account id>`.  These logs are also not natively portable to cloudwatch or datadog.
* API Gateway v2, the technology behind the Command API, publishes access logs to cloudwatch under the log group `/aws/apigateway/<environment>>-ds-private-command-api`.  Note also that these logs are the only places where you can see integration errors between the API Gateway amd Lambda services, for example issues where the output from the lambda

### Lambda Logs

AWS Lambda functions sit behind the Command API endpoints and also perform other asynchronous operations for the service, for example virus/safety scans.  If API Gateway access logs report, for example, a 500 error you can got to the cloudwatch log for the lambda function in question and see a stack trace of the exception.  Lambda log groups are named like `/aws/lambda/<environment>-<function-name>>`.  CloudWatch logs are also exported to datadog.

## Metrics
TBD
- datadog guide
- runbooks for typical support cases

# Architecture Overview

The Document Storage Service is designed to be a very scalable, secure, and cost-effective solution for storing loan-related documents for Numerated.  This was developed as a replacement for Citrix ShareFile.  It uses best-of-breed serverless technology from AWS, including S3, Lambda, CloudFront, WAFv2, API Gateway v2, DynamoDB, SNS, and SQS.  We also use the open-source [ClamAV](https://www.clamav.net/) software for virus/malware scanning.


## Background Reading

* [API Gateway v2 HTTP endpoints](https://docs.aws.amazon.com/apigateway/latest/developerguide/http-api.html)
* [API Gateway v2 Lambda Integrations](https://docs.aws.amazon.com/apigateway/latest/developerguide/http-api-develop-integrations-lambda.html)
* [Presigned URLs for Download](https://docs.aws.amazon.com/AmazonS3/latest/dev/ShareObjectPreSignedURL.html)
* [Presigned URLs for Upload](https://docs.aws.amazon.com/AmazonS3/latest/dev/PresignedUrlUploadObject.html)

## Annotated Diagrams

The Document Storage Service currently works in concert with the Numerated Platform, regardless of whether the platform is deployed to COCC, FIS, or AWS.

The following diagrams map out the moving parts that are part of the service and how it interacts with neighboring services.

* [Architecture Diagram](https://app.lucidchart.com/documents/view/d0c425ee-943f-4cd2-914b-b6f2b0f3f404/0_0)
* [Sequence Diagrams](docs/sequence.md)


## Security Notes
TBD

## ClamAV

We run the open-source ClamAV software to perform safety scans for all new files coming into the service.  Specifically, we've installed the following programs:
* freshclam - a virus definition update utility
* clamd - a dameon used to hold the definitions in memory and perform scans via socket connection.
* clamdscan - a client program used to send scanning instructions to the daamon via socket

### How it works

We deploy all of the binaries/configuration for ClamAV to a lambda layer and attach it to our Perform Safety Scan lambda function. This prevents us from having to deploy it often - it does not change.  We also include binary dependencies as well, to avoid a situation where AWS changes the base image for lambda - we don't want things to suddenly stop working.
 
When the lambda function starts up to scan a workload (cold start), it will first check to see if it has virus definitions installed.  If not, it will use `freshclam` to download and initialize the virus definition database to `/tmp`, over 100MB worth of data.  Next, we see if `clamd` is running by looking for its socket in `/tmp`.  If it's not running, we start it.  These two steps carry a significant performance penalty of roughly 40 seconds, so therefore we try to keep the lambdas warm.  Lastly we will use `clamsdscan` to perform a scan on the file(s) in the workload.  When primed, we can easily complete a scanning workload in less than a second.

### Update Procedure

The original binaries that we deploy from `cicd/clamav_package/bin/` came from an `amazonlinux` docker container.  We deploy everything to the layer because we don't trust that the AWS lambda image won't suddenly change without warning - we don't want to have a dependency disappear.  However, what if you needed to upgrade ClamAV or a binary went missing?

Assuming you've installed the Docker daemon, you can run the following to get yourself into a container where we can get the binaries. This assumes you've obtained the [dependency copier](https://github.com/easternlabs/developer-setup/tree/master#copy-dependencies-from-a-linux-binary):

```bash
docker install amazonlinux
mkdir ~/docker_mount
cp ~/dep_copier.sh ~/docker_mount/dep_copier.sh
docker run -it -v ~/docker_mount:/tmp amazonlinux /bin/bash
```

Now from the docker container, run:
```bash
amazon-linux-extras install epel
yum install clamav clamd -y
sed -i -e "s/^Example/#Example/" /etc/clamd.d/scan.conf
sed -i -e "s/^Example/#Example/" /etc/freshclam.conf
cp /usr/bin/clamdscan /tmp/clamdscan
cp /usr/bin/freshclam /tmp/freshclam
cp /usr/sbin/clamd /tmp/clamd
cp /etc/clamd.d/scan.conf /tmp/clamd.conf
cp /etc/freshclam.conf /tmp/freshclam.conf
bash /tmp/dep_copier.sh /tmp/freshclam /tmp
bash /tmp/dep_copier.sh /tmp/clamd /tmp
bash /tmp/dep_copier.sh /tmp/clamdscan /tmp
```

This will copy all the files you need to deploy ClamAV, though you will probably need to edit the config files.


## Limitations

### File Size

This service is able to store files in S3 and as such is limited only by [AWS's limits for S3](https://aws.amazon.com/s3/faqs/#:~:text=Individual%20Amazon%20S3%20objects%20can,using%20the%20Multipart%20Upload%20capability.).  However as a product, we impose an upload limit of 50MB for an individual file in client-side code.  Large files affect the process of building zip archives and virus scanning.

The max scannable file size in ClamAV can be set [here](cicd/clamav_package/bin/clamd.conf) if the limit needs to change.

### Load
TBD

### Known Issues
TBD