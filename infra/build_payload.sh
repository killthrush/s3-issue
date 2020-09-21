#!/usr/bin/env bash

# Build deployment package for the load test apparatus
# TODO: We probably need a makefile soon, this is getting too complex

install_dependencies_through_docker () {
  echo "Installing dependencies through docker, this may take a few minutes..."
  docker run -v "$PWD":/var/task "lambci/lambda:build-python3.8" /bin/sh -c " \
    pip install --upgrade pip; \
    pip install -r requirements.txt -t infra/.test_package/ --upgrade --use-feature=2020-resolver; \
    chown -R $(id -u):$(id -g) infra/.test_package ; \
    exit"
}

rm -r infra/.test_package
install_dependencies_through_docker
cp -rf src/ infra/.test_package/src


if [ -d "infra/.test_package" ]; then
  cd infra/.test_package && zip -q ../.test.zip -r * && cd ../../
fi