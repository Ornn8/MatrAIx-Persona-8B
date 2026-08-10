#!/usr/bin/env bash
set -euo pipefail

# The shared survey environment writes /app/output/survey_result.json.
# This task intentionally has no hand-authored answer key.
mkdir -p /app/output
