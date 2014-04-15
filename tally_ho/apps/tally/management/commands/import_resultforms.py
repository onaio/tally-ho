#!/usr/bin/env python

from optparse import make_option

from django.core.management.base import BaseCommand
from django.utils.translation import ugettext_lazy

import tally_ho.apps.tally.management.commands.import_data as imp

RESULT_FORMS_PATH = 'data/new_result_forms.csv'


class Command(imp.Command):
    help = ugettext_lazy("Import polling data.")
    option_list = BaseCommand.option_list + (
        make_option('--result-forms-path'),
    )

    def handle(self, *args, **options):
        result_path = options.get('result_forms_path')
        result_path = result_path \
            if result_path is not None else RESULT_FORMS_PATH

        print '[INFO] import result forms'
        self.import_result_forms(result_path)
