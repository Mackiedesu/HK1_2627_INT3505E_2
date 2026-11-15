#!/usr/bin/env bash
# Run Newman CLI against the Books API Postman collection and export JUnit XML report
set -euo pipefail

npx newman run books-api.postman_collection.json \
  -e postman/local.postman_environment.json \
  -r cli,junit \
  --reporter-junit-export reports/junit.xml
