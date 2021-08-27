# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [Unreleased]

### Added

### Changed
- [internal] Upgraded RIBS

### Deprecated

### Removed

### Fixed

### Security

## [v0.5.10]

### Changed
- Limited the situations where the ruby-related line deleting happened

## [v0.5.9]

### Changed
- [internal] Enabled Lazy loading of rust reports

## [v0.5.8]

### Changed
- [internal] Upgraded RIBS

### Added
- Ability to load PEMS from base64 encoded envvars

### Fixed
- Allowed empty layout values
- Fixed corner case in Node where some partials could have been counted as hits

## [v0.5.7]

### Changed
- [internal] Upgraded RIBS

## [v0.5.6]

### Changed
- [internal] Changed logic for single-session totals calculation

## [v0.5.5]

### Changed
- Upgraded RIBS for performance reasons

## [v0.5.4]

### Fixed
- Fixed pickling of TorngitClientError
- Fixed complexity calculation on filtered reports
- Fixed bug on YAML being not a dict

## [v0.5.3]

### Changed
- [INTERNAL] Changed location of celery config in order to have consistent celery rules

### Fixed
- [CE-3240] Fixed Bitbucket API calls on what pertains to teams

## [v0.5.2]

### Fixed
- Corrected some exceptions on YAML errors
- Made ignore_lines clear less caches
- Made `threshold` nullable on some fields

## [v0.5.1]

### Added

### Changed
- Replaced library for validating YAMLs

### Deprecated

### Removed
- [INTERNAL] Removed pycurl

### Fixed
- Fixed small cache discrepancy for when ignore-lines was used

### Security

## [v0.5.0]

### Changed
- Now `totals.coverage` can be None if the totals have no lines
- `totals.files` will only count files that have at least some coverage in them under that given analysis

### Fixed
- `emails` are properly collected using `get_authenticated_user`
- Issues on `analytics` call will no longer crash the rest of the code if they crash

## [v0.4.15]

### Added

### Changed
- Changed prefix-matching behavior on flags filtering to exact-matching. Old behavior can be achiaved on setting `get_config("compatibility", "flag_pattern_matching")` to True

### Deprecated

### Removed

### Fixed
- [CE-3152] Fixed bug where a loss of integrity on some commits could cause descendant commits to not carryforward properly from it

### Security
- Loosened dependencies so package upgrades can happen more easily

## [v0.4.12]

### Added
- Implemented Bitbucket Oauth1 functions

## [v0.4.10]

### Added
- Added `flag_management` field and subfields to user YAML


[unreleased]: https://github.com/codecov/shared/compare/v0.4.13...HEAD
[v0.4.13]: https://github.com/codecov/shared/compare/v0.4.12...v0.4.13
[v0.4.12]: https://github.com/codecov/shared/compare/v0.4.11...v0.4.12
[v0.4.11]: https://github.com/codecov/shared/compare/v0.4.10...v0.4.11
[v0.4.10]: https://github.com/codecov/shared/compare/v0.4.9...v0.4.10
