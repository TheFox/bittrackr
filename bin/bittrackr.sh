#!/usr/bin/env bash

SCRIPT_BASEDIR=$(dirname "$0")
cd "${SCRIPT_BASEDIR}/.."
source ./.venv/bin/activate

./src/bittrackr.py "$@"
