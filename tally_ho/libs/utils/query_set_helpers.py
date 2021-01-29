from django.db import transaction, connection
from django.db.models import ExpressionWrapper, Count, Q, F, FloatField,\
    Func, Subquery, OuterRef, Case, IntegerField, When, Value as V
from tally_ho.apps.tally.models.tally import Tally
from tally_ho.apps.tally.models.result import Result
from tally_ho.apps.tally.models.result_form import ResultForm
from tally_ho.apps.tally.models.station import Station
from tally_ho.libs.models.enums.entry_version import EntryVersion
from tally_ho.libs.models.enums.form_state import FormState


class Cast(Func):
    function = 'CAST'
    template = '%(function)s(%(expressions)s AS %(db_type)s)'

    def __init__(self, expression, db_type):
        # convert second positional argument to kwarg to be used in
        # function template
        super(Cast, self).__init__(expression, db_type=db_type)


def Round(expr, digits=0, output_field=FloatField()):
    # converting to numeric is necessary for postgres
    return ExpressionWrapper(
      Func(Cast(expr, 'numeric'),
           digits,
           function='ROUND'), output_field=output_field)


def build_all_candidates_votes_queryset():
    """
    Create a queryset for all candidates votes in the available active tallies.

    returns: queryset of all candidates votes.
    """
    template = '%(function)s(%(expressions)s AS FLOAT)'
    stations_completed =\
        Func(F('stations_completed'), function='CAST', template=template)
    stations = Func(F('stations'), function='CAST', template=template)
    ew = Round((100 * stations_completed/stations), digits=3)

    station_id_query =\
        Subquery(
            Station.objects.filter(
                tally__id=OuterRef('tally_id'),
                center__code=OuterRef('center_code'))
            .values('id')[:1],
            output_field=IntegerField())
    result_form_center_code_sub_query =\
        Subquery(
            ResultForm.objects.filter(
                ballot__number=OuterRef('ballot_number'),
                tally__id=OuterRef('tally_id')).values(
                    'center__code'
            )[:1], output_field=IntegerField())

    result_form_center_id_sub_query =\
        Subquery(
            ResultForm.objects.filter(
                ballot__number=OuterRef('ballot_number'),
                tally__id=OuterRef('tally_id')).values(
                    'center__id'
            )[:1], output_field=IntegerField())

    candidate_votes_query =\
        Subquery(
            Result.objects.filter(
                candidate__tally__id=OuterRef('tally_id'),
                candidate__id=OuterRef('candidate_id'),
                entry_version=EntryVersion.FINAL,
                result_form__form_state=FormState.ARCHIVED,
                active=True).annotate(
                    candidate_votes=Case(
                        When(votes__isnull=False,
                             then=F('votes')),
                        default=V(0),
                        output_field=IntegerField())).values(
                            'candidate_votes'
                        )[:1], output_field=IntegerField())

    all_candidate_votes_query =\
        Subquery(
            Result.objects.filter(
                candidate__tally__id=OuterRef('tally_id'),
                candidate__id=OuterRef('candidate_id'),
                entry_version=EntryVersion.FINAL,
                active=True).filter(
                    Q(result_form__form_state=FormState.ARCHIVED) |
                    Q(result_form__form_state=FormState.AUDIT)
            ).annotate(
                    candidate_votes=Case(
                        When(votes__isnull=False,
                             then=F('votes')),
                        default=V(0),
                        output_field=IntegerField())).values(
                            'candidate_votes'
            )[:1], output_field=IntegerField())

    qs = Tally.objects.filter(active=True)\
        .values('ballots__candidates__full_name')\
        .annotate(
            tally_id=F('id'),
            ballot_number=F('ballots__number'),
            candidate_id=F('ballots__candidates__id'),
            candidate_active=F('ballots__candidates__active'),
            stations=Count(
                'ballots__resultform__set',
                filter=Q(ballots__resultform__tally__id=F('tally_id'),
                         ballots__resultform__center__isnull=False,
                         ballots__resultform__station_number__isnull=False,
                         ballots__resultform__ballot__isnull=False)
                ),
            center_code=result_form_center_code_sub_query,
            center_id=result_form_center_id_sub_query,
            station_number=F('ballots__resultform__station_number'),
            station_id=station_id_query,
            stations_completed=Count(
                'ballots__resultform__set',
                filter=Q(
                    ballots__resultform__tally__id=F('tally_id'),
                    ballots__resultform__center__isnull=False,
                    ballots__resultform__station_number__isnull=False,
                    ballots__resultform__ballot__isnull=False,
                    ballots__resultform__form_state=FormState.ARCHIVED)
            ),
            votes=candidate_votes_query,
            total_votes=Case(
                When(
                    votes__isnull=False,
                    then=F('votes')
                ),
                default=V(0),
                output_field=IntegerField()
            ),
            all_candidate_votes=all_candidate_votes_query,
            candidate_votes_included_quarantine=Case(
                When(
                    all_candidate_votes__isnull=False,
                    then=F('all_candidate_votes')
                ),
                default=V(0),
                output_field=IntegerField()
            ),
            stations_complete_percent=Case(
                When(stations__gt=0, then=ew),
                default=V(0),
                output_field=FloatField()
            ))

    return qs


@transaction.atomic
def refresh_all_candidates_votes_materiliazed_view():
    with connection.cursor() as cursor:
        cursor.execute(
            "REFRESH MATERIALIZED VIEW CONCURRENTLY tally_allcandidatesvotes")
