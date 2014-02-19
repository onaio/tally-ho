from random import randint

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.utils.translation import ugettext_lazy

from libya_tally.apps.tally.models.result import Result
from libya_tally.apps.tally.models.result_form import ResultForm
from libya_tally.libs.models.enums.entry_version import EntryVersion
from libya_tally.libs.models.enums.form_state import FormState


class Command(BaseCommand):
    help = ugettext_lazy("Create demo users with roles/groups.")

    def handle(self, *args, **kwargs):
        self.fill_all_results()

    def fill_all_results(self):
        Result.objects.all().delete()

        user = User.objects.all()[0]
        for i, result_form in enumerate(ResultForm.objects.all()):
            if i % 100 == 0:
                print 'Result Form %d' % i

            for candidate in result_form.ballot.candidates.all():
                Result.objects.create(result_form=result_form,
                                      user=user,
                                      candidate=candidate,
                                      votes=randint(1, 200),
                                      entry_version=EntryVersion.FINAL)

            if result_form.form_state == FormState.UNSUBMITTED:
                result_form.form_state = FormState.INTAKE
                result_form.save()
                result_form.form_state = FormState.DATA_ENTRY_1
                result_form.save()
                result_form.form_state = FormState.DATA_ENTRY_2
                result_form.save()
                result_form.form_state = FormState.CORRECTION
                result_form.save()
                result_form.form_state = FormState.QUALITY_CONTROL
                result_form.save()
                result_form.form_state = FormState.ARCHIVING
                result_form.save()
                result_form.form_state = FormState.ARCHIVED
                result_form.save()
