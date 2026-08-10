#!/bin/bash
set -euo pipefail

# The shared survey runtime writes survey_result.json. This file is retained as
# a task-bundle reference and intentionally does not fabricate diary answers.
mkdir -p /app/output

