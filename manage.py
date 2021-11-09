#!/usr/bin/env python
import os
import sys

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE",
                          "tally_ho.settings.default")
    # Drop --with-coverage arg if passed
    if '--with-coverage' in sys.argv:
        sys.argv.remove('--with-coverage')

    is_testing = 'test' in sys.argv
    if is_testing:
        import coverage
        cov = coverage.coverage(
            source=['tally_ho'],
            omit=['*/tests/*',
                  'manage.py',
                  'tally_ho/wsgi.py',
                  '*/migrations/*',
                  '*/venv/*'
                  '*/settings/*',
                  '*/templates/*'])
        cov.set_option('report:show_missing', True)
        cov.set_option('report:skip_covered', True)
        cov.erase()
        cov.start()

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)

    if is_testing:
        cov.stop()
        cov.save()
        cov.html_report(directory='covhtml')
        cov.report()
