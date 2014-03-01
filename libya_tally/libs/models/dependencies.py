from django.db.models import Count
from django.utils.translation import ugettext_lazy as _


def check_results_for_forms(resultforms):
    if resultforms.aggregate(Count('results')).values()[0] > 0:
        barcodes_with_results = [r.barcode for r in resultforms
                                 if r.count()]

        raise Exception(_(u'Results exist for barcodes: %s' %
                          barcodes_with_results))
