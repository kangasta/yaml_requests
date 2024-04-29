class RequestLogger:
    def __init__(self):
        self._requests = []

    def copy(self, **kwargs):
        return RequestLogger()

    def start(self):
        pass

    @property
    def requests(self):
        return self._requests

    def error(self, error):
        raise error

    def title(self, name, num_requests, repeat_index=None):
        pass

    def push(self, update):
        pass

    def summary(self, rows):
        pass

    def start_request(self, request):
        self._requests.append(request)

    def close(self):
        pass

    def finish_request(self, request):
        self._requests[-1] = request
