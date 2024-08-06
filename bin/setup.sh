#!/usr/bin/env bash

SCRIPT_BASEDIR=$(dirname "$0")

which virtualenv &> /dev/null || { echo 'ERROR: virtualenv not found in PATH'; exit 1; }

cd "${SCRIPT_BASEDIR}/.."

if ! virtualenv --system-site-packages -p python3 ./.venv ; then
	echo 'ERROR: could not install venv'
	exit 1
fi

if [[ -d ./.venv ]]; then
	source ./.venv/bin/activate
fi

echo '-> installing requirements'
pip install --upgrade pip
if ! pip3 install -r requirements.txt ; then
	echo 'ERROR: could not install requirements'
	exit 1
fi
