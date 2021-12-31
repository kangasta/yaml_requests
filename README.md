# yaml_requests

[![CI](https://github.com/kangasta/yaml_requests/actions/workflows/ci.yml/badge.svg)](https://github.com/kangasta/yaml_requests/actions/workflows/ci.yml)
[![Release](https://github.com/kangasta/yaml_requests/actions/workflows/release.yml/badge.svg)](https://github.com/kangasta/yaml_requests/actions/workflows/release.yml)

A simple python app for sending a set of consecutive HTTP requests defined in YAML requests plan.

## Installing

Ensure that you are using Python >= 3.7 with `python --version`. To install, run:

```bash
pip install yaml_requests
```

## Usage

The app is used to execute HTTP requests defined in YAML files. The YAML file must contain main-level key `requests`, that contains an array of requests, where each item of the list is a request object. The request object contains at least a method key (`get`, `post`, `options`, ...) which value is passed to `requests.request(...)` function.

Minimal YAML request plan should thus include requests array, with single item in it:

```yaml
requests:
- get:
    url: https://google.com
```

In addition to this basic behavior, more advanced features are provided as well:

- All value fields in requests array items support jinja2 templating.
- Variables can be defined in YAML request plan and overridden from commandline arguments.
- Response of the most recent request is stored in `response` variable.
- Responses can be stored as variables with `register` keyword.

More advanded example that can be run against dummy API provided by [tst/server/api.py](./tst/server/api.py):

```yaml
name: Simulate execution of a build from queue
variables:
  base_url: http://localhost:5000
  node: default
requests:
- name: Get queued items
  get:
    url: "{{ base_url }}/queue"
- name: "Create build for first item in the queue ({{ response.json().0.id }})"
  post:
    url: "{{ base_url }}/queue/{{ response.json().0.id }}/init"
    json:
      node: "{{ node }}"
  register: build_create
- name: "Complete the created build ({{ response.json().build_id }})"
  post:
    url: "{{ base_url }}/builds/{{ response.json().build_id }}/complete"
- name: Output build details
  get:
    url: "{{ base_url }}/builds/{{ build_create.json().build_id }}"
  output: yaml
```

These two examples are also available in [tst](./tst) directory and can be executed with:

```sh
yaml_requests tst/minimal_plan.yml
yaml_requests tst/build_queue.yml
```

See `yaml_requests --help` for full CLI usage.

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
