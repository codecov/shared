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

To get started, ensure that you have:

1. Docker installed on your machine
2. Run
```
docker compose up
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

In order to run tests from within your docker container, run:

```
make test
```

## Running migrations

If you make changes to the models in `shared/django_apps/` you will need to create migrations to reflect those changes in the database.

Make sure the shared container is running and shell into it
```bash
$ docker compose up
$ docker compose exec -it shared /bin/bash
```

Now you can create a migration (from within the container)

```bash
$ cd shared/django_apps/
$ python manage.py makemigrations
```

To learn more about migrations visit [Django Docs](https://docs.djangoproject.com/en/5.0/topics/migrations/)

## Managing shared dependencies

As a normal python package, `shared` can include dependencies of its own.

Updating them should be done at the `setup.py` file.

Remember to add dependencies as loosely as possible. Only make sure to include what the minimum version is, and only include a maximum version if you do know that higher versions will break.

Remember that multiple packages, on different contexts of their own requirements, will have to install this. So keeping the requirements loose allow them to avoid version clashes and eases upgrades whenever they need to.

## Contributing

This repository, like all of Codecov's repositories, strives to follow our general [Contributing guidlines](https://github.com/codecov/contributing). If you're considering making a contribution to this repository, we encourage review of our Contributing guidelines first. 
