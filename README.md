# yaml_requests

[![CI](https://github.com/kangasta/yaml_requests/actions/workflows/ci.yml/badge.svg)](https://github.com/kangasta/yaml_requests/actions/workflows/ci.yml)
[![Release](https://github.com/kangasta/yaml_requests/actions/workflows/release.yml/badge.svg)](https://github.com/kangasta/yaml_requests/actions/workflows/release.yml)

A simple python app for sending a set of http requests defined as yaml.

## Installing

Ensure that you are using Python >= 3.7 with `python --version`. To install, run:

```bash
pip install yaml_requests
```

## Testing

Check and automatically fix formatting with:

```bash
pycodestyle yaml_requests
autopep8 -aaar --in-place yaml_requests
```

Run static analysis with:

```bash
pylint -E --enable=invalid-name,unused-import,useless-object-inheritance yaml_requests
```

Run unit tests with command:

```bash
python3 -m unittest discover -s tst/
```

Get test coverage with commands:

```bash
coverage run --branch --source yaml_requests/ -m unittest discover -s tst/
coverage report -m
```
