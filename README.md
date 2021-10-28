# Tesla Cooler (Software) - `tesla_cooler` 

![](./image.jpg)

Firmware for the Raspberry Pi Pico to drive fans and cool NVIDIA Tesla compute GPUs.

See: [esologic.com/tesla-cooler](https://www.esologic.com/tesla-cooler)

## Usage

With the virtual env activated, and your Pico at port `/dev/ttyACM0` run: 

```
rshell -p /dev/ttyACM0 --buffer-size 512 -f command.txt
```

This will upload the library files only to the pico.

## Getting Started

### Python Dependencies

See the `requirements` directory for required Python modules for building, testing, developing etc.
They can all be installed in a [virtual environment](https://docs.python.org/3/library/venv.html) 
using the follow commands:

```
python3 -m venv venv
source venv/bin/activate
pip install -r ./requirements/dev.txt -r ./requirements/prod.txt -r ./requirements/test.txt
```

There's also a bin script to do this:

```
./tools/create_venv.sh
```

### `micropy-cli` usage

The `micropy.json` file describes the MicroPython version that this firmware is designed to run on.
with the virtual environment activated, run:

```
micropy
```

And stubs required to make development easier will be installed in a local `.micropy` directory.

Read more about `micropy-cli` [here](https://github.com/BradenM/micropy-cli).

## Developer Guide

The following is documentation for developers that would like to contribute
to Tesla Cooler.

### Pycharm Note

Make sure you mark `tesla_cooler` and `./test` as source roots!

### Testing

This project uses pytest to manage and run unit tests. Unit tests located in the `test` directory 
are automatically run during the CI build. You can run them manually with:

```
./tools/run_tests.sh
```

### Local Linting

There are a few linters/code checks included with this project to speed up the development process:

* Black - An automatic code formatter, never think about python style again.
* Isort - Automatically organizes imports in your modules.
* Pylint - Check your code against many of the python style guide rules.
* Mypy - Check your code to make sure it is properly typed.

You can run these tools automatically in check mode, meaning you will get an error if any of them
would not pass with:

```
./tools/run_checks.sh
```

Or actually automatically apply the fixes with:

```
./tools/apply_linters.sh
```

There are also scripts in `./tools/` that include run/check for each individual tool.


### Using pre-commit

First you need to init the repo as a git repo with:

```
git init
```

Then you can set up the git hook scripts with:

```
pre-commit install
```

By default:

* black
* pylint
* isort
* mypy

Are all run in apply-mode and must pass in order to actually make the commit.

Also by default, pytest needs to pass before you can push.

If you'd like skip these checks you can commit with:

```
git commit --no-verify
```

If you'd like to quickly run these pre-commit checks on all files (not just the staged ones) you
can run:

```
pre-commit run --all-files
```
