import logging

from django_nose import NoseTestSuiteRunner


class DisableLoggingNoseTestSuiteRunner(NoseTestSuiteRunner):
    """
    Disable the test runner log level below `logging.CRITICAL`.
    """
    def run_tests(self, *args, **kwargs):
        # Disable logging below critical
        logging.disable(logging.CRITICAL)
        super(DisableLoggingNoseTestSuiteRunner, self).run_tests(*args, **kwargs)