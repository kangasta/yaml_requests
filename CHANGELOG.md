# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- `variable_files` plan keyword for reading variables from JSON or YAML file.
- Print requests context to the console.

### Fixed

- If a request in a loop fails, skip following requests unless `ignore_errors` is truthy.
- If parsing plan fails, print error or skipped message for each resolved plan argument.

## [0.15.0]

### Added

- `repeat_delay` option to plan for configuring a delay to wait before repeating the plan execution.

### Fixed

- If `repeat_while` condition is falsy after initial execution, do not repeat the plan.

## [0.14.0]

### Added

- `loop` option to request to allow sending multiple similar requests by looping over list of values.

### Removed

- Drop Python 3.8 support.

## [0.13.0]

### Added

- `lookup` function for reading environment variables and files into string values.
- `open` function for opening files.

## [0.12.0]

### Added

- Support for executing multiple plans at once.
- Support for running plans in parallel.

[unreleased]: https://github.com/kangasta/yaml_requests/compare/v0.15.0...HEAD
[0.15.0]: https://github.com/kangasta/yaml_requests/compare/v0.14.0...v0.15.0
[0.14.0]: https://github.com/kangasta/yaml_requests/compare/v0.13.0...v0.14.0
[0.13.0]: https://github.com/kangasta/yaml_requests/compare/v0.12.0...v0.13.0
[0.12.0]: https://github.com/kangasta/yaml_requests/compare/v0.11.0...v0.12.0
