#!/usr/bin/env bash

# NOTE - this script is current configured to not fail on 
# no test cases run.  See comment below for adjustments
# to the script once ocde and tests are written

# Run all pytest unit tests in the ./otto:./test directory.
# Will exit non-zero if any unit test fail unexpectedly.
# Also runs test coverage check, and will exit non-zero if
# the coerage percentage is below the threshold
#
# Pass in other pytest args, such as for very verbose test output:
#   export PYTEST_EXTRA_ARGS=-vv
#
# On the command line, the optional first argument is the expression to select marked tests.
# The default is 'all' tests, an example expression is "not integration".
# Use an empty string or the special value 'all' for all tests.
# Any additional arguments, directories and filenames are passed to pytest.

set -uo pipefail
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

cd ${DIR}/..
source ./venv/bin/activate

export PYTHONPATH="./tesla_cooler:./test${PYTHONPATH+:}${PYTHONPATH:-}"

TEST_MARKED=${1:-all}
if [ "${1:-}" ]; then shift 1; fi

echo "run tests: ${TEST_MARKED}; args: ${PYTEST_EXTRA_ARGS:-} $@"

coverage erase # clean up any leftover results
coverage run --branch venv/bin/pytest --doctest-modules -m "${TEST_MARKED}" ${@:-test}
# save exit code, so we can run the coverage before exiting
test_res=$?
coverage report --fail-under=85 --skip-covered
# save exit code, so we can fail appropriately
cov_res=$?
coverage html # save the HTML report off for an artifact
coverage erase # clean up our results

echo "test_res, cov_res: " $test_res $cov_res
# see if the tests failed and return their exit status
# NOTE - once the project has code and tests, remove the inner 'if'
if [ $test_res -ne 0 ]
then
    if [ $test_res -eq 5 ]
    then
        echo "NOTICE: no tests run - is this expected?"
        exit 0
    fi
    exit $test_res
fi

# otherwise return the coverage exit status
# NOTE - this check can be removed once there are tests in the created project
if [ $cov_res -eq 5 ]
then
    exit 0 # exit code 5 means no files were checked, necessary for cookiecutter initial creation
fi
exit $cov_res

