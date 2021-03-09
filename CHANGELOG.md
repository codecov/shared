# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [Unreleased]

### Added

### Changed

### Deprecated

### Removed

### Fixed

### Security

## [v0.4.13]

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
