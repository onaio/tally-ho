from random import randint

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.utils.translation import ugettext_lazy

from tally_ho.apps.tally.models.result import Result
from tally_ho.apps.tally.models.result_form import ResultForm
from tally_ho.libs.models.enums.entry_version import EntryVersion
from tally_ho.libs.models.enums.form_state import FormState


class Command(BaseCommand):
    help = ugettext_lazy("Create fake results for each result form.")

    def handle(self, *args, **kwargs):
        self.fill_all_results()

    def fill_all_results(self):
        Result.objects.all().delete()

        user = User.objects.all()[0]
        for i, result_form in enumerate(ResultForm.objects.all()):
            if i % 100 == 0:
                print 'Result Form %d' % i

            if result_form.form_state == FormState.UNSUBMITTED and\
                    result_form.ballot:
                for candidate in result_form.ballot.candidates.all():
                    Result.objects.create(result_form=result_form,
                                          user=user,
                                          candidate=candidate,
                                          votes=randint(1, 200),
                                          entry_version=EntryVersion.FINAL)

                for state in [FormState.INTAKE,
                              FormState.DATA_ENTRY_1,
                              FormState.DATA_ENTRY_2,
                              FormState.CORRECTION,
                              FormState.QUALITY_CONTROL,
                              FormState.ARCHIVING,
                              FormState.ARCHIVED]:
                    result_form.form_state = state
                    result_form.save()
