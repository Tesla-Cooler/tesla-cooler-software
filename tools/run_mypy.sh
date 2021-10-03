#!/usr/bin/env bash

# Run mypy in check mode to ensure that there are no missing types
# Will exit non-zero if there are errors or incorrectly formatted python imports.

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

cd ${DIR}/..
source ./venv/bin/activate

export PYTHONPATH="./tesla_cooler:./test${PYTHONPATH+:}${PYTHONPATH:-}"

mypy --show-error-codes main.py  # Run on loose files within this project
mypy --show-error-codes -p tesla_cooler -p test  # Run on sub-packages within this project

