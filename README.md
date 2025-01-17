# yaml_requests

[![CI](https://github.com/kangasta/yaml_requests/actions/workflows/ci.yml/badge.svg)](https://github.com/kangasta/yaml_requests/actions/workflows/ci.yml)
[![Release](https://github.com/kangasta/yaml_requests/actions/workflows/release.yml/badge.svg)](https://github.com/kangasta/yaml_requests/actions/workflows/release.yml)
[![Maintainability](https://api.codeclimate.com/v1/badges/c1f5aaa1355b50f202d8/maintainability)](https://codeclimate.com/github/kangasta/yaml_requests/maintainability)
[![Test Coverage](https://api.codeclimate.com/v1/badges/c1f5aaa1355b50f202d8/test_coverage)](https://codeclimate.com/github/kangasta/yaml_requests/test_coverage)

<!-- Start docs include -->

A simple python app for sending a set of consecutive HTTP requests defined in YAML requests plan.

## Installing

Ensure that you are using Python >= 3.9 with `python --version`. This app/package is available in [PyPI](https://pypi.org/project/yaml-requests/). To install, run:

```bash
pip install yaml_requests
```

## Usage

The app is used to execute HTTP requests defined in YAML files. The YAML file must contain main-level key `requests`, that contains an array of requests, where each item of the list is a request object. The request object contains at least a method key (`get`, `post`, `options`, ...) which value is passed to [`requests.request`](https://docs.python-requests.org/en/latest/api/#requests.request) function, or to [`requests.Session.request`](https://docs.python-requests.org/en/latest/api/#requests.Session.request) if plan level option `session` is truthy.

Minimal YAML request plan should thus include requests array, with single item in it:

```yaml
requests:
- get:
    url: https://google.com
```

In addition to this basic behavior, more advanced features are provided as well:

- All value fields in requests array items support jinja2 templating.
- Values can be read from environment variables with `lookup` function. For example, `{{ lookup("env", "API_TOKEN") }}`.
- Files can be read as text with `lookup` function (e.g., `{{ lookup("file", "headers.yaml")}}`) or opened with `open` function (e.g. `{{ open("photos/eiffer-tower.jpg") }}`) to pass in as file objects to `files` parameter of request functions.
- Variables can be defined in YAML request plan and overridden from commandline arguments.
- Response of the most recent request is stored in `response` variable as [`requests.Response`](https://docs.python-requests.org/en/latest/api/#requests.Response) object.
- Responses can be stored as variables with `register` keyword.
- Response can be verified with assertions.
- Plan execution can be repeated by setting `repeat_while` option.
- Request can be looped by defining `loop` option for a request. The current item is available in `item` variable.

<!-- End docs include -->

See documentation for [API reference](https://kangasta.github.io/yaml_requests/yaml_requests.html#api-reference).

## Advanced Example

Here is an advanced example:

```yaml
name: Simulate execution of a build from queue
variables:
  base_url: http://localhost:5000
  node: default
requests:
- name: Get queued items
  get:
    url: "{{ base_url }}/queue"
  assert:
  - name: Queue is not empty
    expression: response.json() | length
  - name: Status code is 200
    expression: response.status_code == 200
  - name: Request took less than 5 seconds
    expression: response.elapsed.total_seconds() < 5
  register: queue_response_1
- name: "Create build for first item in the queue ({{ response.json().0.id }})"
  post:
    url: "{{ base_url }}/queue/{{ response.json().0.id }}/init"
    json:
      node: "{{ node }}"
  register: build_create
- name: Get queued items
  get:
    url: "{{ base_url }}/queue"
  assert:
  - name: Queue is shorter than initially
    expression: response.json() | length < queue_response_1.json() | length
- name: "Complete the created build ({{ build_create.json().build_id }})"
  post:
    url: "{{ base_url }}/builds/{{ build_create.json().build_id }}/complete"
- name: Output build details
  get:
    url: "{{ base_url }}/builds/{{ build_create.json().build_id }}"
  output: yaml
```

### Running the Example

This example can be run against the dummy API provided by [tst/server/api.py](./tst/server/api.py)

Start by making sure that `flask` is installed:

```bash
python -m pip install flask
```

Then run the test server:

```bash
python -m flask --app tst/server/api.py run
```

With the test server running execute the plan using the command:

```bash
yaml_requests tst/plans/integration/build_queue.yml
```

### More examples

There are more examples available in [tst/plans](./tst/plans) directory and can be executed as follows:

```sh
yaml_requests tst/plans/minimal_plan.yml
yaml_requests tst/plans/integration/build_queue.yml
```

## Help

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
