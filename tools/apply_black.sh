#!/usr/bin/env bash

# Run Black - change code to make sure that python code is properly formatted.

set -euo pipefail
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

cd ${DIR}/..
source ./venv/bin/activate

LC_ALL=C.UTF-8 LANG=C.UTF-8 black ./main.py . -l 100 --exclude=venv
