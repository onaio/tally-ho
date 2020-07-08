#!/usr/bin/env python
import os
import sys

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE",
                          "tally_ho.settings.default")
    is_testing = 'test' in sys.argv
    if is_testing:
        import coverage
        cov = coverage.coverage(
            source=['.'],
            omit=['*/tests/*',
                  'manage.py',
                  'tally_ho/wsgi.py',
                  '*/migrations/*',
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
