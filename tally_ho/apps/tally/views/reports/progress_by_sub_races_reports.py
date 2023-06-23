from django.urls import reverse
from django.http import JsonResponse

from django.shortcuts import render
from tally_ho.apps.tally.models.office import Office
from tally_ho.apps.tally.models.region import Region
from tally_ho.apps.tally.models.constituency import Constituency
from tally_ho.apps.tally.models.sub_constituency import SubConstituency
from tally_ho.apps.tally.models.result_form import ResultForm
from tally_ho.libs.models.enums.race_type import RaceType
from tally_ho.libs.utils.context_processors import (
    get_datatables_language_de_from_locale
)
from django.db.models import F
from tally_ho.libs.models.enums.form_state import FormState


def progress_report(request, **kwargs):
    tally_id = kwargs.get('tally_id')
    language_de = get_datatables_language_de_from_locale(request)

    dt_offices_columns = [{ "data": "office_name" }]
    html_table_offices_columns = ["Office"]

    dt_regions_columns = [{ "data": "region_name" }]
    html_table_regions_columns = ["Region"]

    dt_constituencies_columns = [{"data": "constituency_name"}]
    html_table_constituencies_columns = ["Constituency"]

    dt_sub_constituencies_columns = [{"data": "sub_constituency_code"}]
    html_table_sub_constituencies_columns = ["Sub Constituency"]

    for race in RaceType:
        dt_offices_columns.append({ "data": race.name.lower() })
        dt_offices_columns.append({
            "data": f"{race.name.lower()}_percentage"
        })
        html_table_offices_columns.append(race.name)
        html_table_offices_columns.append("%")

        dt_regions_columns.append({ "data": race.name.lower() })
        dt_regions_columns.append({
            "data": f"{race.name.lower()}_percentage"
        })
        html_table_regions_columns.append(race.name)
        html_table_regions_columns.append("%")

        dt_constituencies_columns.append({"data": race.name.lower()})
        dt_constituencies_columns.append({
            "data": f"{race.name.lower()}_percentage"
        })
        html_table_constituencies_columns.append(race.name)
        html_table_constituencies_columns.append("%")

        dt_sub_constituencies_columns.append({"data": race.name.lower()})
        dt_sub_constituencies_columns.append({
            "data": f"{race.name.lower()}_percentage"
        })
        html_table_sub_constituencies_columns.append(race.name)
        html_table_sub_constituencies_columns.append("%")

    dt_offices_columns.append({ "data": "overall" })
    dt_offices_columns.append({ "data": "overall_percentage" })
    html_table_offices_columns.append("Overall")
    html_table_offices_columns.append("%")

    dt_regions_columns.append({ "data": "overall" })
    dt_regions_columns.append({ "data": "overall_percentage" })
    html_table_regions_columns.append("Overall")
    html_table_regions_columns.append("%")

    dt_constituencies_columns.append({"data": "overall"})
    dt_constituencies_columns.append({"data": "overall_percentage"})
    html_table_constituencies_columns.append("Overall")
    html_table_constituencies_columns.append("%")

    dt_sub_constituencies_columns.append({"data": "overall"})
    dt_sub_constituencies_columns.append({"data": "overall_percentage"})
    html_table_sub_constituencies_columns.append("Overall")
    html_table_sub_constituencies_columns.append("%")

    context = {
        'tally_id': tally_id,
        'offices_progress_report_url': reverse(
            'offices-progress-report', kwargs=kwargs),
        'regions_progress_report_url': reverse(
            'regions_progress-report', kwargs=kwargs),
        'constituencies_progress_report_url': reverse(
            'constituencies-progress-report', kwargs=kwargs),
        'sub_constituencies_progress_report_url': reverse(
            'sub-constituencies-progress-report', kwargs=kwargs),
        'languageDE': language_de,
        'dt_offices_columns': dt_offices_columns,
        'html_table_offices_columns': html_table_offices_columns,
        'dt_regions_columns': dt_regions_columns,
        'html_table_regions_columns': html_table_regions_columns,
        'dt_constituencies_columns': dt_constituencies_columns,
        'html_table_constituencies_columns': html_table_constituencies_columns,
        'dt_sub_constituencies_columns': dt_sub_constituencies_columns,
        'html_table_sub_constituencies_columns':
            html_table_sub_constituencies_columns,
    }
    return render(
        request, 'reports/progress_report_by_admin_area.html', context)


def regions_progress_report_view(request, **kwargs):
    tally_id = kwargs.get('tally_id')
    regions_report =\
        Region.objects.filter(tally_id=tally_id).annotate(
            region_name=F('name')
        ).values('region_name')
    regions_report = list(regions_report)

    for region_report in regions_report:
        region_name = region_report.get('region_name')
        total_forms_processed = 0
        total_forms_expected = 0
        for race in RaceType:
            qs =\
                ResultForm.objects.filter(
                    tally__id=tally_id,
                    center__region=region_name,
                    ballot__race_type=race,
                    barcode__isnull=False,
                )
            forms_expected = qs.count()
            total_forms_expected += forms_expected

            if forms_expected == 0:
                region_report[race.name.lower()] = "0/0"
                region_report[f'{race.name.lower()}_percentage'] = "0"
                region_report['overall'] = "0/0"
                region_report['overall_percentage'] = "0"
                continue

            forms_processed =\
                qs.filter(form_state=FormState.ARCHIVED).count()
            total_forms_processed += forms_processed
            region_report[race.name.lower()] =\
                f"{forms_processed}/{forms_expected}"
            region_report[f'{race.name.lower()}_percentage'] =\
                round(100 * forms_processed / forms_expected, 2) if forms_expected else 0.0
        region_report['overall'] =\
            f"{total_forms_processed}/{total_forms_expected}"
        region_report['overall_percentage'] =\
            round(100 * total_forms_processed / total_forms_expected, 2) if total_forms_expected else 0.0

    sorted_regions_report =\
        sorted(regions_report, key=lambda x: -x['overall_percentage'])
    return JsonResponse({
        'data': sorted_regions_report,
        'draw': 1,
        'recordsFiltered': len(sorted_regions_report),
        'recordsTotal': len(sorted_regions_report),
        'results': 'ok'})


def offices_progress_report_view(request, **kwargs):
    tally_id = kwargs.get('tally_id')
    offices_report =\
        Office.objects.filter(tally_id=tally_id).annotate(
            office_name=F('name')
        ).values('office_name')
    offices_report = list(offices_report)

    for office_report in offices_report:
        office_name = office_report.get('office_name')
        total_forms_processed = 0
        total_forms_expected = 0
        for race in RaceType:
            qs =\
                ResultForm.objects.filter(
                    tally__id=tally_id,
                    center__office__name=office_name,
                    ballot__race_type=race,
                    barcode__isnull=False,
                )
            forms_expected = qs.count()
            total_forms_expected += forms_expected

            if forms_expected == 0:
                office_report[race.name.lower()] = "0/0"
                office_report[f'{race.name.lower()}_percentage'] = "0"
                office_report['overall'] = "0/0"
                office_report['overall_percentage'] = "0"
                continue

            forms_processed =\
                qs.filter(form_state=FormState.ARCHIVED).count()
            total_forms_processed += forms_processed

            office_report[race.name.lower()] =\
                f"{forms_processed}/{forms_expected}"
            office_report[f'{race.name.lower()}_percentage'] =\
                round(100 * forms_processed / forms_expected, 2) if forms_expected else 0.0
        office_report['overall'] =\
            f"{total_forms_processed}/{total_forms_expected}"
        office_report['overall_percentage'] =\
            round(100 * total_forms_processed / total_forms_expected, 2) if total_forms_expected else 0.0

    sorted_offices_report =\
        sorted(offices_report, key=lambda x: -x['overall_percentage'])
    return JsonResponse({
        'data': sorted_offices_report,
        'draw': 1,
        'recordsFiltered': len(sorted_offices_report),
        'recordsTotal': len(sorted_offices_report),
        'results': 'ok'})


def constituencies_progress_report_view(request, **kwargs):
    tally_id = kwargs.get('tally_id')
    constituencies_report = \
        Constituency.objects.filter(tally_id=tally_id).annotate(
            constituency_name=F('name')
        ).values('constituency_name')
    constituencies_report = list(constituencies_report)

    for constituency_report in constituencies_report:
        constituency_name = constituency_report.get('constituency_name')
        total_forms_processed = 0
        total_forms_expected = 0
        for race in RaceType:
            qs = \
                ResultForm.objects.filter(
                    tally__id=tally_id,
                    center__constituency__name=constituency_name,
                    ballot__race_type=race,
                    barcode__isnull=False,
                )
            forms_expected = qs.count()
            total_forms_expected += forms_expected

            if forms_expected == 0:
                constituency_report[race.name.lower()] = "0/0"
                constituency_report[f'{race.name.lower()}_percentage'] = "0"
                constituency_report['overall'] = "0/0"
                constituency_report['overall_percentage'] = "0"
                continue

            forms_processed = \
                qs.filter(form_state=FormState.ARCHIVED).count()
            total_forms_processed += forms_processed

            constituency_report[race.name.lower()] = \
                f"{forms_processed}/{forms_expected}"
            constituency_report[f'{race.name.lower()}_percentage'] = \
                round(100 * forms_processed / forms_expected, 2) if forms_expected else 0.0
        constituency_report['overall'] = \
            f"{total_forms_processed}/{total_forms_expected}"
        constituency_report['overall_percentage'] = \
            round(100 * total_forms_processed / total_forms_expected, 2) if total_forms_expected else 0.0

    sorted_constituencies_report = \
        sorted(constituencies_report, key=lambda x: -x['overall_percentage'])
    return JsonResponse({
        'data': sorted_constituencies_report,
        'draw': 1,
        'recordsFiltered': len(sorted_constituencies_report),
        'recordsTotal': len(sorted_constituencies_report),
        'results': 'ok'})


def sub_constituencies_progress_report_view(request, **kwargs):
    tally_id = kwargs.get('tally_id')
    sub_constituencies_report = \
        SubConstituency.objects.filter(tally_id=tally_id).annotate(
            sub_constituency_code=F('code')
        ).values('sub_constituency_code')
    sub_constituencies_report = list(sub_constituencies_report)

    for sub_constituency_report in sub_constituencies_report:
        sub_constituency_code = sub_constituency_report.get('sub_constituency_code')
        total_forms_processed = 0
        total_forms_expected = 0
        for race in RaceType:
            qs = \
                ResultForm.objects.filter(
                    tally__id=tally_id,
                    center__sub_constituency__code=sub_constituency_code,
                    ballot__race_type=race,
                    barcode__isnull=False,
                )
            forms_expected = qs.count()
            total_forms_expected += forms_expected

            if forms_expected == 0:
                sub_constituency_report[race.name.lower()] = "0/0"
                sub_constituency_report[f'{race.name.lower()}_percentage'] = "0"
                sub_constituency_report['overall'] = "0/0"
                sub_constituency_report['overall_percentage'] = "0"
                continue

            forms_processed = \
                qs.filter(form_state=FormState.ARCHIVED).count()
            total_forms_processed += forms_processed

            sub_constituency_report[race.name.lower()] = \
                f"{forms_processed}/{forms_expected}"
            sub_constituency_report[f'{race.name.lower()}_percentage'] = \
                round(100 * forms_processed / forms_expected, 2) if forms_expected else 0.0
        sub_constituency_report['overall'] = \
            f"{total_forms_processed}/{total_forms_expected}"
        sub_constituency_report['overall_percentage'] = \
            round(100 * total_forms_processed / total_forms_expected, 2) if total_forms_expected else 0.0

    sorted_sub_constituencies_report = \
        sorted(sub_constituencies_report, key=lambda x: -x['overall_percentage'])
    return JsonResponse({
        'data': sorted_sub_constituencies_report,
        'draw': 1,
        'recordsFiltered': len(sorted_sub_constituencies_report),
        'recordsTotal': len(sorted_sub_constituencies_report),
        'results': 'ok'})