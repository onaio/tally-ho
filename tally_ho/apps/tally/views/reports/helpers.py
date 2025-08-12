from django.db.models import (
    Case,
    CharField,
    Count,
    F,
    IntegerField,
    OuterRef,
    Q,
    Subquery,
    Sum,
    When,
)
from django.db.models import Value as V

from tally_ho.apps.tally.models.result_form import ResultForm
from tally_ho.apps.tally.models.station import Station
from tally_ho.libs.models.enums.form_state import FormState
from tally_ho.libs.utils.query_set_helpers import Round


def get_filtered_candidate_votes(
    tally_id,
    qs,
    data=None):
    """
    Genarate a report of votes per candidate.

    :param tally_id: The tally id.
    :param qs: The result parent queryset.
    :param data: An array of dicts containing centers and stations
        id's to filter out from the queryset.

    returns: The votes per candidate queryset.
    """
    query_args = {}
    station_total_result_forms_sub_query =\
        Subquery(
            ResultForm.objects.filter(
                tally__id=tally_id,
                center__code=OuterRef('center__code'),
                station_number=OuterRef('station_number')
            ).values('center__code', 'station_number').annotate(
                total_result_forms=Count(
                    'barcode',
                    distinct=True
                ),
            ).values('total_result_forms')[:1], output_field=IntegerField())

    station_total_result_forms_archived_sub_query =\
        Subquery(
            ResultForm.objects.filter(
                tally__id=tally_id,
                center__code=OuterRef('center__code'),
                station_number=OuterRef('station_number')
            ).values('center__code', 'station_number').annotate(
                total_result_forms_archived=Count(
                    'barcode',
                    distinct=True,
                    filter=Q(form_state=FormState.ARCHIVED)
                ),
            ).values('total_result_forms_archived')[:1],
            output_field=IntegerField())

    if data:
        selected_center_ids =\
            data['select_1_ids'] if data.get('select_1_ids') else []
        selected_station_ids =\
            data['select_2_ids'] if data.get('select_2_ids') else []
        election_level_names = data['election_level_names'] \
            if data.get('election_level_names') else []
        sub_race_type_names = data['sub_race_type_names'] \
            if data.get('sub_race_type_names') else []
        ballot_status = data['ballot_status'] \
            if data.get('ballot_status') else []
        station_status = data['station_status'] \
            if data.get('station_status') else []
        candidate_status = data['candidate_status'] \
            if data.get('candidate_status') else []
        sub_con_codes = data['sub_con_codes'] \
            if data.get('sub_con_codes') else []
        percentage_processed = data['percentage_processed'] \
            if data.get('percentage_processed') else 0
        stations_processed_percentage = min(int(percentage_processed), 100)

        stations_qs = Station.objects.filter(
                        tally__id=tally_id,
                        center__resultform__isnull=False,
                    )
        if station_status:
            if len(station_status) == 1:
                station_status = station_status[0]
                if station_status == 'active':
                    active = True
                else:
                    active = False
                if selected_station_ids:
                    stations_qs = stations_qs.filter(
                        id__in=selected_station_ids,
                        active=active
                    )
                elif selected_center_ids:
                    stations_qs = stations_qs.filter(
                        center__id__in=selected_center_ids,
                        active=active
                    )
                stations_qs = stations_qs.filter(
                    active=active
                )
                selected_station_ids = \
                    [item.get('id') for item in stations_qs.values('id')
                     ] if stations_qs.values('id') else [0]

        if stations_processed_percentage:
            if selected_station_ids:
                stations_qs = stations_qs.filter(
                    id__in=selected_station_ids,
                )
            elif selected_center_ids:
                stations_qs = stations_qs.filter(
                    center__id__in=selected_center_ids,
                )

            stations_qs = stations_qs.values('id').annotate(
                total_result_forms=station_total_result_forms_sub_query,
                total_result_forms_archived=
                station_total_result_forms_archived_sub_query,
                processed_percentage=Round(
                    100 * F('total_result_forms_archived') / F(
                        'total_result_forms'),
                    digits=2
                )).filter(
                processed_percentage__gte=stations_processed_percentage)
            selected_station_ids = \
                [item.get('id') for item in stations_qs
                 ] if stations_qs else [0]

        if sub_race_type_names:
            sub_race_type_field =\
                'candidate__ballot__electrol_race__ballot_name__in'
            query_args[sub_race_type_field] =\
                sub_race_type_names

        if sub_con_codes:
            sub_con_code_field =\
                'result_form__center__sub_constituency__code__in'
            query_args[sub_con_code_field] =\
                sub_con_codes

        if election_level_names:
            election_level_field =\
                'candidate__ballot__electrol_race__election_level__in'
            query_args[election_level_field] =\
                election_level_names

        if ballot_status:
            if len(ballot_status) == 1:
                ballot_status = ballot_status[0]
                if ballot_status == 'available_for_release':
                    available_for_release = True
                else:
                    available_for_release = False
                query_args['candidate__ballot__available_for_release'] =\
                    available_for_release

        if candidate_status:
            if len(candidate_status) == 1:
                candidate_status = candidate_status[0]
                if candidate_status == 'active':
                    active = True
                else:
                    active = False
                query_args['candidate__active'] = active

        if selected_station_ids or stations_processed_percentage:
            station_id_query =\
                Subquery(
                    Station.objects.filter(
                        tally__id=tally_id,
                        center__code=OuterRef(
                            'result_form__center__code'),
                        station_number=OuterRef(
                            'result_form__station_number'))
                    .values('id')[:1],
                    output_field=IntegerField())
            qs = qs\
                .annotate(station_ids=station_id_query)
            qs = qs.filter(
                Q(station_ids__in=selected_station_ids))

        elif selected_center_ids:
            qs = qs.filter(
                Q(result_form__center__id__in=selected_center_ids))

    queryset = (
        qs\
        .filter(**query_args)
        .values(
            'candidate__candidate_id',
            'candidate__ballot__number',
            'candidate__ballot__electrol_race__id',
            'candidate__ballot__electrol_race__election_level',
            'candidate__ballot__electrol_race__ballot_name',
        )\
        .annotate(
            candidate_number=F('candidate__candidate_id'),
            candidate_name=F('candidate__full_name'),
            ballot_number=F('candidate__ballot__number'),
            total_votes=Sum('votes'),
            order=F('candidate__order'),
            candidate_status=Case(
                When(
                    candidate__active=True,
                    then=V('enabled')
                ), default=V('disabled'), output_field=CharField()),
            electrol_race_id=F(
                'candidate__ballot__electrol_race__id'),
            election_level=F(
                'candidate__ballot__electrol_race__election_level'),
            sub_race_type=F(
                'candidate__ballot__electrol_race__ballot_name'),
        )
    )
    return queryset
