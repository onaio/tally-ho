from django import forms
from django.utils.translation import ugettext_lazy as _

from tally_ho.apps.tally.models.candidate import Candidate
from tally_ho.apps.tally.models.center import Center
from tally_ho.apps.tally.models.comment import Comment
from tally_ho.apps.tally.models.station import Station
from tally_ho.apps.tally.models.ballot import Ballot


def disable_enable_entity(center_code,
                          station_number,
                          disable_reason=None,
                          comment_text=None,
                          tally_id=None):
    entities = []
    entity_to_return = None
    status_target = False
    try:
        if station_number:
            entity_to_return = Station.objects.get(
                station_number=station_number,
                center__code=center_code,
                center__tally__id=tally_id)
            status_target = not entity_to_return.active

            entities.append(entity_to_return)
        else:
            entity_to_return = Center.objects.get(code=center_code,
                                                  tally__id=tally_id)
            status_target = not entity_to_return.active

            entities.append(entity_to_return)
            entities += Station.objects.filter(center__code=center_code,
                                               center__tally__id=tally_id)
    except Center.DoesNotExist:
        raise forms.ValidationError(_('Center Number does not exist'))
    except Station.DoesNotExist:
        raise forms.ValidationError(_('Station Number does not exist'))
    else:
        if comment_text:
            comment = Comment(text=comment_text, tally_id=tally_id)

            if station_number:
                comment.station = entity_to_return
            else:
                comment.center = entity_to_return

            comment.save()

        for entity in entities:
            entity.active = status_target

            entity.disable_reason = 0
            if disable_reason is not None:
                entity.disable_reason = disable_reason

            entity.save()
        return entity_to_return


def disable_enable_race(race_id,
                        disable_reason=None,
                        comment=None,
                        tally_id=None):
    race = None

    try:
        race = Ballot.objects.get(id=race_id)

    except Ballot.DoesNotExist:
        raise forms.ValidationError(_('Race does not exist'))
    else:
        if comment:
            Comment(text=comment, ballot=race, tally_id=tally_id).save()

        race.active = not race.active
        race.disable_reason = 0

        if disable_reason is not None:
            race.disable_reason = disable_reason

        race.save()
        return race


def disable_enable_candidate(candidate_id):
    entity_to_return = None
    status_target = False

    try:
        entity_to_return = Candidate.objects.get(id=candidate_id)
        status_target = not entity_to_return.active

    except Candidate.DoesNotExist:
        raise forms.ValidationError(_('Candidate does not exist'))
    else:
        entity_to_return.active = status_target
        entity_to_return.save()

        return entity_to_return
