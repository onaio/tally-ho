from django.contrib.postgres.aggregates.general import ArrayAgg
from django.db import transaction, connection
from django.db.models import ExpressionWrapper, Count, Q, F, FloatField,\
    Func, Subquery, OuterRef, Case, IntegerField, When, Value as V
from collections import defaultdict
from django.apps import apps

from tally_ho.apps.tally.models.result import Result
from tally_ho.apps.tally.models.candidate import Candidate
from tally_ho.libs.models.enums.entry_version import EntryVersion
from tally_ho.libs.models.enums.form_state import FormState
from tally_ho.libs.utils.cache_model_instances_count_to_memcache import (
    cache_model_instances_count_to_memcache
)


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


def build_tally_candidates_votes_queryset():
    """
    Create a queryset for all candidates votes in a tally.

    returns: queryset of all candidates votes.
    """
    template = '%(function)s(%(expressions)s AS FLOAT)'
    stations_completed =\
        Func(F('stations_completed'), function='CAST', template=template)
    stations = Func(F('stations'), function='CAST', template=template)
    ew = Round((100 * stations_completed/stations), digits=3)

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

    qs = Candidate.objects.all()\
        .values('full_name')\
        .annotate(
            tally_id=F('tally__id'),
            candidate_id=F('id'),
            ballot_number=F('ballot__number'),
            candidate_active=F('active'),
            stations=Count(
                'ballot__resultform',
                filter=Q(ballot__resultform__tally__id=F('tally_id'),
                         ballot__resultform__center__isnull=False,
                         ballot__resultform__station_number__isnull=False,
                         ballot__resultform__ballot__isnull=False)
            ),
            stations_completed=Count(
                'ballot__resultform',
                filter=Q(
                    ballot__resultform__tally__id=F('tally_id'),
                    ballot__resultform__center__isnull=False,
                    ballot__resultform__station_number__isnull=False,
                    ballot__resultform__ballot__isnull=False,
                    ballot__resultform__form_state=FormState.ARCHIVED)
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
            ),
            center_ids=ArrayAgg(
                'ballot__resultform__center__id',
                distinct=True),
            station_numbers=ArrayAgg(
                'ballot__resultform__station_number',
                distinct=True))

    return qs


@transaction.atomic
def refresh_all_candidates_votes_materiliazed_view():
    with connection.cursor() as cursor:
        cursor.execute(
            "REFRESH MATERIALIZED VIEW CONCURRENTLY tally_allcandidatesvotes")


class BulkCreateManager(object):
    """
    This helper class keeps track of ORM objects to be created for multiple
    model classes, and automatically creates those objects with `bulk_create`
    when the number of objects accumulated for a given model class exceeds or
    equals `chunk_size`.
    Upon completion of the loop that's `add()`ing objects, the developer must
    call `done()` to ensure the final set of objects is created for all models.
    """

    def __init__(
            self,
            objs_count=None,
            chunk_size=None,
            cache_instances_count=False,
            cache_key=None,
            memcache_client=None,
        ):
        self.create_queues = defaultdict(list)
        self.cache_instances_count = cache_instances_count
        self.memcache_client = memcache_client
        self.cache_key = cache_key
        self.default_chunk_size = 500
        self.chunk_size = chunk_size or self._calculate_chuck_size(objs_count)

    def _calculate_chuck_size(self, objs_count):
        chunk_size =\
            objs_count if objs_count and objs_count < self.default_chunk_size\
                else self.default_chunk_size
        return chunk_size

    def _commit(self, model_class, objs, last_chunk=False):
        instances = model_class.objects.bulk_create(objs)
        if self.cache_instances_count:
            cache_model_instances_count_to_memcache(
                self.cache_key, len(instances),
                done=last_chunk,
                memcache_client=self.memcache_client)
        return instances

    def add(self, obj):
        """
        Add an object to the queue to be created, and call bulk_create if we
        have enough objs.
        """
        model_class = type(obj)
        model_key = model_class._meta.label
        self.create_queues[model_key].append(obj)
        if len(self.create_queues[model_key]) >= self.chunk_size:
            self._commit(model_class, self.create_queues[model_key])
            self.create_queues[model_key] = []

    def done(self):
        """
        Always call this upon completion to make sure the final partial chunk
        is saved.
        """
        for model_name, objs in self.create_queues.items():
            if len(objs) > 0:
                self._commit(
                    apps.get_model(model_name),
                    objs=objs,
                    last_chunk=True)

class BulkUpdateManyToManyManager(object):
    """
    This helper class keeps track of Model instances with many to many fields
    to be updated and automatically updates those instances when the number of
    instances accumulated for a given model class exceeds or equals
    `chunk_size`.
    Upon completion of the loop that's `add()`ing instances, the developer must
    call `done()` to ensure the final set of instances is updated for all
    models.
    """

    def __init__(
            self,
            instances_count=None,
            chunk_size=None,
            cache_instances_count=False,
            memcache_client=None,
            cache_key=None):
        self._queue = defaultdict(list)
        self.default_chunk_size = 100
        self.cache_instances_count = cache_instances_count
        self.memcache_client = memcache_client
        self.cache_key = cache_key
        self.chunk_size =\
            chunk_size or self._calculate_chuck_size(instances_count)

    def _calculate_chuck_size(self, instances_count):
        chunk_size =\
            instances_count if instances_count and\
                instances_count < self.default_chunk_size\
                else self.default_chunk_size
        return chunk_size

    def _set_many_to_many_fields_in_instances(
            self,
            instances_list=None,
            last_chunk=False):
        with transaction.atomic():
            for item in instances_list:
                many_to_many_obj = item.get('many_to_many_fields')
                for many_to_many_field_name in many_to_many_obj.keys():
                    getattr(item.get('instance'),
                            many_to_many_field_name).set(
                        many_to_many_obj.get(many_to_many_field_name))
            if self.cache_instances_count:
                cache_model_instances_count_to_memcache(
                    self.cache_key,
                    len(instances_list),
                    done=last_chunk,
                    memcache_client=self.memcache_client)

    def add(self, instance_obj=None):
        model_key = instance_obj.get('instance')._meta.label
        self._queue[model_key].append(instance_obj)
        if len(self._queue[model_key]) >= self.chunk_size:
            instances_list = self._queue[model_key]
            self._queue[model_key] = []
            # Set many to many fields in instances
            self._set_many_to_many_fields_in_instances(
                instances_list=instances_list,
            )

    def done(self):
        """
        Always call this upon completion to make sure the final partial chunk
        is saved.
        """
        for model_name, objs in self._queue.items():
                if len(objs) > 0:
                    # Set many to many fields in instances
                    self._set_many_to_many_fields_in_instances(
                        instances_list=objs,
                        last_chunk=True
                    )
                    self._queue[model_name] = []
