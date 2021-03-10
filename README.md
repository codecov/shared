# shared

Shared is a place for code that is common to multiple python repositories on `codecov`.

## How does shared get into production

`shared` is a repository of its own, so it needs to be installed as a dependency on the reporitories that might use it.

The current repositories using `shared` are `codecov/worker` and `codecov/codecov-api`.

Whenever getting new code into `shared`, one needs to wait for a new version to be release (or release it themselves, see below), and put such version on worker and api `requirements.in`

## Releasing a new version on shared

To release a new version, you need to:

1) Check what the next version should be.
    - You can check the latest version on https://github.com/codecov/shared/releases
    - As a rule of thumb, just add one to the micro version (number most to the right)
2) Create a new PR:
- Changing the `version` field on https://github.com/codecov/shared/blob/master/setup.py#L12 to that new version
- Change https://github.com/codecov/shared/blob/master/CHANGELOG.md  unreleased header name to that version, and create a new _unreleased_ section with the same subsections.
3) Merge that PR
4) Create a new release on https://github.com/codecov/shared/releases/new