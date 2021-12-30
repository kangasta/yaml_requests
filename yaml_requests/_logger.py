from threading import Event, Thread

# From cli-spinners (https://www.npmjs.com/package/cli-spinners)
INTERVAL = 0.080  # seconds
FRAMES = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏']

COLORS = dict(red=31, green=32, yellow=33, blue=34)


def _print_spinner_and_text(text, stop_event):
    i = 0
    while not stop_event.wait(INTERVAL):
        print(f'\r{FRAMES[i % len(FRAMES)]} {text}', end='')
        i += 1
    print('\r', end='')


def get_color(response):
    if response and response.ok:
        return 'green'
    return 'red'


def get_symbol(response):
    if response and response.ok:
        return '✔'
    return '✘'


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

    def start(self, name, method, params):
        text = self.bold(
            name) if name else f'{self.bold(method)} {params.get("url")}'

        if self._animations:
            self._active = Thread(
                target=_print_spinner_and_text, args=[
                    text, self._stop_event])
            self._stop_event.clear()
            self._active.start()

    def finish(self, name, method, params, response=None, error=None):
        self._stop_event.set()
        if self._active:
            self._active.join()
            self._active = None

        symbol_text = self.color(
            get_symbol(response), get_color(response))
        name_text = f'{self.bold(name)}\n  ' if name else ''
        code_text = self.bold(
            f'HTTP {response.status_code}') if response else ''
        elapsed_ms = response.elapsed.total_seconds() * 1000
        elapsed_text = f' ({elapsed_ms:.3f} ms)' if response else ''
        error_text = f'{self.bold("ERROR:")} {error}' if error else ''

        text = (
            f'{symbol_text} {name_text}'
            f'{self.bold(method)} {params.get("url")}\n  '
            f'{code_text}{error_text}{elapsed_text}\n')

        print(text)
