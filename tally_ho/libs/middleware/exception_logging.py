from django.conf import settings
import logging


logger = logging.getLogger('tally')
handler = logging.FileHandler(getattr(settings,
                                      'LOG_FILE_PATH',
                                      '/var/log/tally-system/logs/tally.log'))
formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.INFO)


class ExceptionLoggingMiddleware(object):
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_exception(self, request, exception):
        logger.exception('Exception handling request for ' + request.path)
