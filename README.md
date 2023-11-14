# shared
[![Shared CI](https://github.com/codecov/shared/actions/workflows/ci.yml/badge.svg)](https://github.com/codecov/shared/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/codecov/shared/graph/badge.svg?token=IL64imgbOu)](https://codecov.io/gh/codecov/shared)  

Shared is a place for code that is common to multiple python repositories on `codecov`.

> We believe that everyone should have access to quality software (like Sentry), that’s why we have always offered Codecov for free to open source maintainers.
>
> By making our code public, we’re not only joining the community that’s supported us from the start — but also want to make sure that every developer can contribute to and build on the Codecov experience.

## How does shared get into production

`shared` is a repository of its own, so it needs to be installed as a dependency on the repositories that might use it.

The current repositories using `shared` are `codecov/worker` and `codecov/codecov-api`.

Whenever getting new code into `shared`, one needs to wait for a new version to be released (or release it themselves, see below), and update the `requirements.in` file in `codecov/worker` and `codecov/codecov-api` to use the newly released version of `shared`.

## Getting started

To get started, you will need a few things due the presence of a rust extension on this package:

1. Have rust installed in your system
2. Have a virtualenv (whichever one you prefer)
3. Run
```
pip install setuptools-rust pip-tools
python setup.py develop
pip install -r requirements.txt -r tests/requirements.txt
```

## Releasing a new version on shared

To release a new version, you need to:

1) Check what the next version should be.
    - You can check the latest version on https://github.com/codecov/shared/releases
    - As a rule of thumb, just add one to the micro version (number most to the right)
2) Create a new PR:
- Changing the `version` field on https://github.com/codecov/shared/blob/main/setup.py#L12 to that new version
- Change https://github.com/codecov/shared/blob/main/CHANGELOG.md  unreleased header name to that version, and create a new _unreleased_ section with the same subsections.
3) Merge that PR
4) Create a new release on https://github.com/codecov/shared/releases/new

## Running tests

In order to run tests, from inside the virtualenv this repo is in:

```
make test
```

## Managing shared dependencies

As a normal python package, `shared` can include dependencies of its own.

Updating them should be done at the `setup.py` file.

Remember to add dependencies as loosely as possible. Only make sure to include what the minimum version is, and only include a maximum version if you do know that higher versions will break.

Remember that multiple packages, on different contexts of their own requirements, will have to install this. So keeping the requirements loose allow them to avoid version clashes and eases upgrades whenever they need to.

# ribs
Rust Service to be called from inside python

This is some rust code that is meant to be installed as a python wheel on the repository and used

It uses [pyo3](https://pyo3.rs) as the binding and [setuptools-rust](https://github.com/PyO3/setuptools-rust) as the tool that turns the rust code into python

We hope it provides a new level of speed to the CPU-bound parts of the code

## Contributing

This repository, like all of Codecov's repositories, strives to follow our general [Contributing guidlines](https://github.com/codecov/contributing). If you're considering making a contribution to this repository, we encourage review of our Contributing guidelines first. 
