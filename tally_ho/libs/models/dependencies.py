from django import forms
from django.db.models import Count
from django.utils.translation import gettext_lazy as _


def check_results_for_forms(resultforms):
    if list((resultforms.aggregate(Count('results')).values()))[0] > 0:
        barcodes_with_results = [r.barcode for r in resultforms
                                 if r.results.count()]

        raise forms.ValidationError(_('Results exist for barcodes:'
                                      f' {barcodes_with_results}'))
