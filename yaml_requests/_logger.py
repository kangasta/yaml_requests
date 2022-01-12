import json
import yaml
import re
from shutil import get_terminal_size
from threading import Event, Thread

from ._request import RequestState

# From cli-spinners (https://www.npmjs.com/package/cli-spinners)
INTERVAL = 0.080  # seconds
FRAMES = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏']

COLORS = dict(red=31, green=32, yellow=33, blue=34, grey=90)


def _fit_to_width(text):
    max_len = get_terminal_size().columns
    non_formatted_text = re.sub(r'\033\[[0-9]+m', '', text.replace('\r', ''))
    if len(non_formatted_text) < max_len:
        return text

    i = 0
    j = 0
    while i < max_len - 2:
        match = re.match(r'\r|\033\[[0-9]+m', text[(i + j):])
        if match:
            j += len(match.group(0))
        else:
            i += 1

    clear_formatting = '\033[0m' if re.search(r'\033\[[0-9]+m', text) else ''
    return f'{text[:(i + j)]}{clear_formatting}…'


def _print_spinner_and_text(text, stop_event):
    i = 0
    while not stop_event.wait(INTERVAL):
        print(_fit_to_width(f'\r{FRAMES[i % len(FRAMES)]} {text}'), end='')
        i += 1
    print('\r', end='')


def get_indicator(state_or_ok):
    if state_or_ok in (RequestState.SUCCESS, RequestState.NOT_RAISED, True,):
        return ('green', '✔',)
    elif state_or_ok in (RequestState.FAILURE, RequestState.ERROR, False,):
        return ('red', '✘',)
    elif state_or_ok == RequestState.SKIPPED:
        return ('blue', '⮟',)


class RequestLogger:
    def __init__(self, animations, colors):
        self._animations = animations
        self._colors = colors

        self._active = None
        self._stop_event = Event()

    def bold(self, text):
        if not self._colors:
            return text
        return f'\033[1m{text}\033[22m'

    def color(self, text, color):
        if not self._colors or color not in COLORS:
            return text
        return f'\033[{COLORS[color]}m{text}\033[0m'

    def error(self, text):
        error_text = self.bold(self.color('ERROR:', 'red'))
        print(f'{error_text} {text}')

    def title(self, name, num_requests):
        name_text = f'{self.bold(name)}\n' if name else ''
        print(f'{name_text}Sending {num_requests} requests:\n')

    def _get_indicator_text(self, request=None, assertion=None):
        color, symbol = get_indicator(
            request.state if request else assertion.ok)
        return self.color(symbol, color)

    def _get_name_text(self, request):
        if request.name:
            return self.bold(request.name)
        return ''

    def _get_method_text(self, request):
        return f'{self.bold(request.method)} {request.params.get("url")}'

    def _get_response_code_text(self, request):
        response = request.response
        if response is None:
            return ''

        code_text = self.bold(f'HTTP {response.status_code}')
        elapsed_ms = response.elapsed.total_seconds() * 1000
        not_raised_text = ''
        if request.state == RequestState.NOT_RAISED:
            not_raised_text = self.color(
                ' HTTP status code ignored.', 'grey')

        return f'{code_text} ({elapsed_ms:.3f} ms){not_raised_text}'

    def _get_message_text(self, request):
        message = request.state.message

        type_text = self.bold(f'{str(request.state).upper()}:')
        return f'{type_text} {message}' if message else ''

    def _get_assertion_text(self, request):
        text = ''

        if request.state == RequestState.SKIPPED:
            return text

        for assertion in request.assertions:
            indicator = self._get_indicator_text(assertion=assertion)
            text += f'\n  {indicator} {assertion.name}'

        return f'{text}\n' if text else ''

    def _headers_text(self, response):
        return '\n'.join(
            f'{self.bold(key)}: {value}' for key,
            value in response.headers.items())

    def _response_output_text(self, response, output):
        def _format_output(output):
            if not output.endswith('\n'):
                output = f'{output}\n'
            output = output.replace('\n', '\n  ').rstrip(' ')
            return f'\n  {output}'

        try:
            if not output:
                return ''
            elif output.lower() == 'headers':
                return _format_output(self._headers_text(response))
            elif output.lower() == 'text':
                return _format_output(response.text)
            elif output.lower() == 'json':
                pretty_json = json.dumps(response.json(), indent=2)
                return _format_output(pretty_json)
            elif output.lower() in ('yml', 'yaml'):
                pretty_yaml = yaml.dump(response.json())
                return _format_output(pretty_yaml)
            else:
                return ''
        except BaseException:
            return ''

    def _response_text(self, request):
        output = request.options.output
        output = output if isinstance(output, list) else [output]
        response = request.response

        return ''.join(self._response_output_text(response, i) for i in output)

    def start_request(self, request):
        if not self._animations:
            return

        text = self._get_name_text(request) or self._get_method_text(request)

        self._active = Thread(
            target=_print_spinner_and_text, args=[
                text, self._stop_event])
        self._stop_event.clear()
        self._active.start()

    def stop_progress_animation(self):
        self._stop_event.set()
        if self._active:
            self._active.join()
            self._active = None

    def finish_request(self, request):
        self.stop_progress_animation()

        name_text = self._get_name_text(request)
        name_separator = name_text and '\n  '
        code_text = self._get_response_code_text(request)
        message_text = self._get_message_text(request)
        message_separator = '\n  ' if message_text and code_text else ''

        text = (
            f'{self._get_indicator_text(request)} {name_text}{name_separator}'
            f'{self._get_method_text(request)}\n  '
            f'{code_text}{message_separator}{message_text}\n'
            f'{self._get_assertion_text(request)}'
            f'{self._response_text(request)}')

        print(text)
