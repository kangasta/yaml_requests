import json
import sys
import yaml

from ciou.color import bold, colors, fg_green, fg_red, fg_hi_black, no_color
from ciou.progress import Checks, MessageStatus, Progress, OutputConfig, Update

from .._request import RequestState


def get_assertion_status(assertion):
    if not assertion.executed:
        return MessageStatus.SKIPPED
    elif assertion.ok:
        return MessageStatus.SUCCESS
    else:
        return MessageStatus.ERROR


def get_status(state):
    if state in (RequestState.SUCCESS, RequestState.NOT_RAISED,):
        return MessageStatus.SUCCESS
    elif state in (RequestState.FAILURE, RequestState.ERROR,):
        return MessageStatus.ERROR
    elif state == RequestState.SKIPPED:
        return MessageStatus.SKIPPED


def _is_printable(pair):
    return isinstance(pair[1], (bool, dict, float, int, list, str))


class ConsoleLogger:
    def __init__(
            self,
            animations=True,
            colors=True,
            target=None,
            log_started=True):
        if not target:
            target = sys.stdout

        self._log_started = log_started

        self._output_config = OutputConfig(
            details_color=no_color,
            disable_animation=(not animations),
            disable_colors=(not colors),
            target=target,
        )
        self._progress = None

    def copy(self, **kwargs):
        current = dict(
            animations=(not self._output_config.disable_animation),
            colors=(not self._output_config.disable_colors),
            target=self._output_config.target,
        )
        return ConsoleLogger(**{**current, **kwargs})

    def start(self):
        self._progress = Progress(config=self._output_config)
        self._progress.start()

    def _style(self, text, *color):
        if self._output_config.disable_colors:
            return text

        return colors(*color)(text)

    def _print(self, *args):
        return print(*args, file=self._output_config.target)

    def close(self):
        if self._progress:
            self._progress.stop()

    def error(self, error):
        text = str(error)
        if not text:
            return

        error_text = self._style('ERROR:', bold, fg_red)
        self._print(f'{error_text} {text}')

    def _repeat_text(self, repeat_index):
        if repeat_index is None:
            return ''
        return f' (repeat_index={repeat_index})'

    def title(self, name, num_requests, repeat_index=None):
        name_text = f'{self._style(name, bold)}\n' if name else ''
        self._print(
            f'{name_text}Sending {num_requests} requests'
            f'{self._repeat_text(repeat_index)}:\n')

    def push(self, update):
        return self._progress.push(update)

    def summary(self, rows):
        key_width = max(len(i[0]) for i in rows) + 1

        for key, value in rows:
            if isinstance(value, list):
                passed, failed, total = value
                values = []

                if passed:
                    values.append(
                        self._style(
                            f'{passed} succeeded',
                            bold,
                            fg_green))
                if failed:
                    values.append(
                        self._style(
                            f'{failed} failed',
                            bold,
                            fg_red))

                values.append(f'{total} total')
                value = ', '.join(values)
            self._print(
                f'{self._style((key + ":").ljust(key_width), bold)} {value}')

    def _get_name_text(self, request):
        if request.name:
            return self._style(request.name, bold)
        return ''

    def _get_method_text(self, request):
        return (
            f'{self._style(request.method, bold)} {request.params.get("url")}')

    def _get_response_code_text(self, request):
        response = request.response
        if response is None:
            return ''

        code_text = self._style(f'HTTP {response.status_code}', bold)
        elapsed_ms = response.elapsed.total_seconds() * 1000
        not_raised_text = ''
        if request.state == RequestState.NOT_RAISED:
            not_raised_text = self._style(
                ' HTTP status code ignored.', fg_hi_black)

        return f'{code_text} ({elapsed_ms:.3f} ms){not_raised_text}'

    def _get_message_text(self, request):
        message = request.state.message

        type_text = self._style(f'{str(request.state).upper()}:', bold)
        return f'{type_text} {message}' if message else ''

    def _get_assertion_text(self, request):
        if request.state == RequestState.SKIPPED:
            return ''

        checks = Checks()
        for assertion in request.assertions:
            checks.push(Update(
                message=assertion.name,
                status=get_assertion_status(assertion),
            ))

        text = checks.getvalue()
        return f'\n{text}' if text else ''

    def _headers_text(self, headers):
        return '\n'.join(
            f'{self._style(key, bold)}: {value}' for key,
            value in headers.items())

    def _variables_text(self, variables):
        return '\n'.join(
            f'{self._style(key, bold)}: {value}' for key,
            value in dict(filter(_is_printable, variables.items())).items())

    def _body_text(self, body, content_type):
        if not isinstance(body, str):
            body = body.decode('utf-8')

        if content_type.startswith('application/json'):
            return json.dumps(
                json.loads(body), indent=2)
        elif content_type.startswith('application/yaml'):
            return yaml.dump(
                yaml.safe_load(body), default_flow_style=False)
        return body

    def _response_output_text(self, request, output):
        response = request.response

        def _format_output(output, prefix=''):
            output = output.rstrip(' \n').replace('\n', f'\n{prefix}')
            if not output.endswith('\n'):
                output = f'{output}\n'
            return f'\n{prefix}{output}'

        try:
            if not output:
                return ''
            elif (output.lower() == 'headers' or
                    output.lower() == 'response_headers'):
                return _format_output(
                    self._headers_text(response.headers), '< ')
            elif output.lower() == 'request_headers':
                return _format_output(
                    self._headers_text(response.request.headers), '> ')
            elif output.lower() == 'request_body':
                raw_body = response.request.body
                content_type = response.request.headers.get('Content-Type')
                return _format_output(
                    self._body_text(raw_body, content_type), '> ')
            elif output.lower() == 'response_body':
                content_type = response.headers.get('Content-Type')
                return _format_output(
                    self._body_text(response.text, content_type), '< ')
            elif output.lower() == 'text':
                return _format_output(response.text, '< ')
            elif output.lower() == 'json':
                pretty_json = json.dumps(response.json(), indent=2)
                return _format_output(pretty_json, '< ')
            elif output.lower() == 'variables':
                return _format_output(
                    self._variables_text(request._template_env.globals))
            elif output.lower() in ('yml', 'yaml'):
                pretty_yaml = yaml.dump(
                    response.json(), default_flow_style=False)
                return _format_output(pretty_yaml, '< ')
            else:
                return _format_output(
                    f'Unknown output entry [{output}], expected one of [\
headers, request_headers, request_body, \
response_headers, response_body, text, json, variables, \
yml, yaml]', '? ')
        except BaseException:
            return ''

    def _response_text(self, request):
        output = request.options.output
        output = output if isinstance(output, list) else [output]

        return ''.join(self._response_output_text(request, i) for i in output)

    def start_request(self, request):
        if not self._log_started:
            return

        text = self._get_name_text(request) or self._get_method_text(request)

        self._progress.push(Update(
            key=request.id,
            message=text,
            status=MessageStatus.STARTED,
        ))

    def finish_request(self, request):
        name_text = self._get_name_text(request)
        message = name_text or self._get_method_text(request)

        method_text = name_text and f'{self._get_method_text(request)}\n'
        code_text = self._get_response_code_text(request)
        message_text = self._get_message_text(request)
        message_separator = '\n  ' if message_text and code_text else ''

        details = (
            f'{method_text}'
            f'{code_text}{message_separator}{message_text}\n'
            f'{self._get_assertion_text(request)}'
            f'{self._response_text(request)}\n')

        self._progress.push(Update(
            key=request.id,
            message=message,
            details=details,
            status=get_status(request.state)
        ))
