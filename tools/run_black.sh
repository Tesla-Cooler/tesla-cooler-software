#!/usr/bin/env bash

# Run black in check mode to ensure that there are not outstanding changes that need to be made.
# Will exit non-zero if there are errors or incorrectly formatted python code.

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

cd ${DIR}/..
source ./venv/bin/activate

LC_ALL=C.UTF-8 LANG=C.UTF-8 black . *.py tesla_cooler/ test/ -l 100 --diff --check --exclude=venv
