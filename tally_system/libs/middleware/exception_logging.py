import logging


logger = logging.getLogger('tally')
handler = logging.FileHandler('/var/log/tally-system/logs/tally.log')
formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.INFO)


class ExceptionLoggingMiddleware(object):

    def process_exception(self, request, exception):
        logger.exception('Exception handling request for ' + request.path)
