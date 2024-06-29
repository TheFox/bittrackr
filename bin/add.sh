#!/usr/bin/env bash

SCRIPT_BASEDIR=$(dirname "$0")
source "${SCRIPT_BASEDIR}/../.venv/bin/activate"
"${SCRIPT_BASEDIR}/../src/add.py" "$@"
