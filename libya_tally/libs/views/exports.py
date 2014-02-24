import csv

from django.http import HttpResponse
from django.utils.encoding import smart_str


def export_to_csv_response(queryset, headers, fields, filename='data.csv'):
    response = HttpResponse(content_type='text/csv')
    response['Content-Desposition'] = 'attachment; filename=%s' % filename

    w = csv.writer(response, csv.excel)
    w.writerow([smart_str(col) for col in headers])

    for obj in queryset:
        row = []
        for field in fields:
            row.append(smart_str(getattr(obj, field)))
        w.writerow(row)

    return response
