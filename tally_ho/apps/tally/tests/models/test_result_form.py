from django.utils.translation import gettext_lazy as _

from tally_ho.apps.tally.models import ResultForm, Station, WorkflowRequest
from tally_ho.apps.tally.models.archive import Archive
from tally_ho.apps.tally.models.quality_control import QualityControl
from tally_ho.apps.tally.models.quarantine_check import QuarantineCheck
from tally_ho.apps.tally.models.result import Result
from tally_ho.apps.tally.models.result_form import sanity_check_final_results
from tally_ho.libs.models.enums.actions_prior import ActionsPrior
from tally_ho.libs.models.enums.audit_resolution import AuditResolution
from tally_ho.libs.models.enums.clearance_resolution import ClearanceResolution
from tally_ho.libs.models.enums.entry_version import EntryVersion
from tally_ho.libs.models.enums.form_state import FormState
from tally_ho.libs.models.enums.gender import Gender
from tally_ho.libs.models.enums.request_reason import RequestReason
from tally_ho.libs.models.enums.request_type import RequestType
from tally_ho.libs.tests.test_base import (TestBase, create_audit,
                                           create_ballot, create_candidate,
                                           create_candidates, create_center,
                                           create_clearance,
                                           create_electrol_race, create_office,
                                           create_reconciliation_form,
                                           create_region, create_result,
                                           create_result_form, create_station,
                                           create_sub_constituency,
                                           create_tally)


class TestResultForm(TestBase):
    def setUp(self):
        self._create_and_login_user()
        self.tally = create_tally()
        self.electrol_race =\
            create_electrol_race(
                self.tally,
                election_level="presidential",
                ballot_name="Presidential"
            )
        self.ballot =\
            create_ballot(
                self.tally,
                electrol_race=self.electrol_race,
                number=1
            )
        self.region = create_region(tally=self.tally)
        self.office =\
            create_office(
                name='Test Office Setup',
                tally=self.tally,
                region=self.region
            )
        self.sub_constituency =\
            create_sub_constituency(tally=self.tally, code=123)
        self.center =\
            create_center(
                code=12345,
                tally=self.tally,
                sub_constituency=self.sub_constituency,
                office_name=self.office.name
            )
        self.station = create_station(self.center, tally=self.tally)

    def test_quality_control(self):
        """Test result form quality control"""
        result_form = create_result_form(
            tally=self.tally,
            ballot=self.ballot,
            center=self.center,
            station_number=self.station.station_number
        )
        quality_control = QualityControl.objects.create(
            result_form=result_form,
            user=self.user
            )
        QualityControl.objects.create(
            result_form=result_form,
            user=self.user,
            active=False
            )

        self.assertEqual(result_form.qualitycontrol, quality_control)

    def test_reconciliation_match(self):
        """Test result form reconciliation match"""
        result_form = create_result_form(
            center=self.center,
            station_number=self.station.station_number,
            ballot=self.ballot,
            tally=self.tally,
            form_state=FormState.CORRECTION
        )
        # No forms yet
        self.assertFalse(result_form.reconciliation_match)

        create_reconciliation_form(
            result_form, self.user, entry_version=EntryVersion.DATA_ENTRY_1)
        # Only one form
        self.assertFalse(result_form.reconciliation_match)

        re_form_2 =\
            create_reconciliation_form(
                result_form, self.user,
                entry_version=EntryVersion.DATA_ENTRY_2
            )
        # Two matching forms
        self.assertTrue(result_form.reconciliation_match)

        # Modify the second form to create mismatch
        re_form_2.number_valid_votes = 999
        re_form_2.save()
        self.assertFalse(result_form.reconciliation_match)

    def test_sanity_check_results(self):
        """Test sanity checks for final results"""
        votes = 12
        result_form = create_result_form(
            tally=self.tally,
            ballot=self.ballot,
            center=self.center,
            station_number=self.station.station_number
        )
        create_candidates(
            result_form, votes=votes, user=self.user,
            num_results=1
            )
        for result in result_form.results.all():
            result.entry_version = EntryVersion.FINAL
            result.save()
            # create duplicate final results
            create_result(result_form, result.candidate, self.user, votes)
        self.assertEqual(result_form.results_final.filter().count(), 4)
        sanity_check_final_results(result_form)
        self.assertEqual(result_form.results_final.filter().count(), 2)

    def test_audit_quarantine_check_name_property_method(self):
        """Test audit quarantine check name property method"""
        result_form = create_result_form(
            tally=self.tally,
            ballot=self.ballot,
            center=self.center,
            station_number=self.station.station_number
        )
        quarantine_check = QuarantineCheck.objects.create(
            user=self.user,
            name='1',
            method='1',
            value=1,
        )
        audit = create_audit(result_form, self.user)
        audit.quarantine_checks.add(quarantine_check)
        self.assertQuerySetEqual(
            result_form.audit_quaritine_checks,
            audit.quarantine_checks.all().values('name')
            )

    def test_station_property(self):
        """Test the station property retrieves the correct station."""
        result_form = create_result_form(
            center=self.center,
            station_number=self.station.station_number,
            tally=self.tally,
            ballot=self.ballot
        )
        self.assertEqual(result_form.station, self.station)

    def test_num_votes_property(self):
        """Test the num_votes property sums final results correctly."""
        result_form = create_result_form(
            tally=self.tally,
            ballot=self.ballot,
            center=self.center,
            station_number=self.station.station_number
        )
        # No results yet
        self.assertEqual(result_form.num_votes, 0)

        candidate1 = create_candidate(self.ballot, "cand1", tally=self.tally)
        candidate2 = create_candidate(self.ballot, "cand2", tally=self.tally)

        create_result(result_form, candidate1, self.user, votes=10)
        create_result(result_form, candidate2, self.user, votes=20)

        # Results are final
        self.assertEqual(result_form.num_votes, 30)

        # Add non-final results (should not be counted)
        Result.objects.create(result_form=result_form,
                          user=self.user,
                          candidate=candidate1,
                          votes=5,
                          entry_version=EntryVersion.DATA_ENTRY_1)
        self.assertEqual(result_form.num_votes, 30)

    def test_has_results_property(self):
        """Test the has_results property."""
        result_form = create_result_form(
            tally=self.tally,
            ballot=self.ballot,
            center=self.center,
            station_number=self.station.station_number
        )
        self.assertFalse(result_form.has_results)

        candidate = create_candidate(self.ballot, "cand1", tally=self.tally)
        create_result(result_form, candidate, self.user, votes=10)
        self.assertTrue(result_form.has_results)

    def test_audit_properties(self):
        """Test properties related to the linked audit."""
        result_form = create_result_form(
            tally=self.tally,
            ballot=self.ballot,
            center=self.center,
            station_number=self.station.station_number
        )
        self.assertIsNone(result_form.audit)
        self.assertEqual(result_form.audit_team_reviewed, _('No'))
        self.assertEqual(result_form.audit_supervisor_reviewed, _('No'))
        self.assertIsNone(result_form.audit_recommendation)
        self.assertIsNone(result_form.audit_action_prior)
        self.assertIsNone(result_form.audit_quaritine_checks)

        audit = create_audit(result_form, self.user, reviewed_team=True)
        audit.supervisor = self.user
        audit.reviewed_supervisor = True
        audit.resolution_recommendation = AuditResolution.EMPTY
        audit.action_prior_to_recommendation =\
            ActionsPrior.REQUEST_AUDIT_ACTION_FROM_FIELD
        audit.save()

        quarantine_check =\
            QuarantineCheck.objects.create(name='check1', method='m1')
        audit.quarantine_checks.add(quarantine_check)

        result_form.refresh_from_db()

        self.assertEqual(
            result_form.audit, audit)
        self.assertEqual(
            result_form.audit_team_reviewed, self.user.username)
        self.assertEqual(
            result_form.audit_supervisor_reviewed, self.user.username)
        self.assertEqual(
            result_form.audit_recommendation, _(AuditResolution.EMPTY.label))
        self.assertEqual(
            result_form.audit_action_prior,
            _(ActionsPrior.REQUEST_AUDIT_ACTION_FROM_FIELD.label))
        self.assertQuerySetEqual(
            result_form.audit_quaritine_checks,
            audit.quarantine_checks.all().values('name'))

    def test_clearance_properties(self):
        """Test properties related to the linked clearance."""
        result_form = create_result_form(
            tally=self.tally,
            ballot=self.ballot,
            center=self.center,
            station_number=self.station.station_number
        )
        self.assertIsNone(result_form.clearance)
        self.assertFalse(result_form.clearance_team_reviewed_bool)
        self.assertEqual(result_form.clearance_team_reviewed, _('No'))
        self.assertEqual(result_form.clearance_supervisor_reviewed, _('No'))
        self.assertIsNone(result_form.clearance_recommendation)
        self.assertIsNone(result_form.clearance_action_prior)

        clearance =\
            create_clearance(result_form, self.user, reviewed_team=True)
        clearance.supervisor = self.user
        clearance.reviewed_supervisor = True
        clearance.resolution_recommendation =\
            ClearanceResolution.PENDING_FIELD_INPUT
        clearance.action_prior_to_recommendation =\
            ActionsPrior.REQUEST_COPY_FROM_FIELD
        clearance.save()

        result_form.refresh_from_db()

        self.assertEqual(result_form.clearance, clearance)
        self.assertTrue(result_form.clearance_team_reviewed_bool)
        self.assertEqual(
            result_form.clearance_team_reviewed, self.user.username)
        self.assertEqual(
            result_form.clearance_supervisor_reviewed, self.user.username)
        self.assertEqual(
            result_form.clearance_recommendation,
            _(ClearanceResolution.PENDING_FIELD_INPUT.label))
        self.assertEqual(
            result_form.clearance_action_prior,
            _(ActionsPrior.REQUEST_COPY_FROM_FIELD.label))

    def test_reconciliationform_properties(self):
        """Test reconciliationform and reconciliationform_exists properties."""
        result_form = create_result_form(
            tally=self.tally,
            ballot=self.ballot,
            center=self.center,
            station_number=self.station.station_number
        )
        self.assertFalse(result_form.reconciliationform_exists)
        self.assertFalse(result_form.reconciliationform)

        create_reconciliation_form(
            result_form, self.user, entry_version=EntryVersion.DATA_ENTRY_1)
        self.assertTrue(result_form.reconciliationform_exists)
        self.assertFalse(result_form.reconciliationform)

        recon_final =\
            create_reconciliation_form(
                result_form, self.user, entry_version=EntryVersion.FINAL)
        self.assertTrue(result_form.reconciliationform_exists)
        self.assertEqual(result_form.reconciliationform, recon_final)

        recon_final_dupe =\
            create_reconciliation_form(
                result_form, self.user, entry_version=EntryVersion.FINAL)
        self.assertEqual(
            result_form.reconciliationform_set.filter(
                active=True, entry_version=EntryVersion.FINAL).count(), 2)

        final_recon_after_clean =\
            result_form.reconciliationform
        self.assertEqual(
            result_form.reconciliationform_set.filter(
                active=True, entry_version=EntryVersion.FINAL).count(), 1)
        self.assertIn(final_recon_after_clean, [recon_final, recon_final_dupe])

    def test_results_match_property(self):
        """Test the results_match property."""
        result_form = create_result_form(
            tally=self.tally,
            ballot=self.ballot,
            center=self.center,
            station_number=self.station.station_number
        )
        candidate1 = create_candidate(self.ballot, "cand1", tally=self.tally)
        candidate2 = create_candidate(self.ballot, "cand2", tally=self.tally)

        # No results yet
        self.assertFalse(result_form.results_match)

        # Matching results DE1 and DE2
        Result.objects.create(result_form=result_form,
                          user=self.user,
                          candidate=candidate1,
                          votes=10,
                          entry_version=EntryVersion.DATA_ENTRY_1)
        Result.objects.create(result_form=result_form,
                          user=self.user,
                          candidate=candidate2,
                          votes=20,
                          entry_version=EntryVersion.DATA_ENTRY_1)
        Result.objects.create(result_form=result_form,
                          user=self.user,
                          candidate=candidate1,
                          votes=10,
                          entry_version=EntryVersion.DATA_ENTRY_2)
        Result.objects.create(result_form=result_form,
                          user=self.user,
                          candidate=candidate2,
                          votes=20,
                          entry_version=EntryVersion.DATA_ENTRY_2)
        self.assertTrue(result_form.results_match)

        result_form.results.filter(
            candidate=candidate2,
            entry_version=EntryVersion.DATA_ENTRY_2).update(votes=25)
        self.assertFalse(result_form.results_match)

    def test_get_matched_results_tracks_previous_state_on_count_mismatch(self):
        """Test get_matched_results tracks previous_form_state on mismatch."""
        from django.core.exceptions import SuspiciousOperation

        from tally_ho.apps.tally.models.result import Result
        from tally_ho.apps.tally.models.result_form import get_matched_results

        result_form = create_result_form(
            form_state=FormState.CORRECTION,
            tally=self.tally,
            ballot=self.ballot,
            center=self.center,
            station_number=self.station.station_number
        )
        initial_state = result_form.form_state

        # Create mismatched result counts (2 for DE1, 1 for DE2)
        candidate1 = create_candidate(self.ballot, "cand1", tally=self.tally)
        candidate2 = create_candidate(self.ballot, "cand2", tally=self.tally)

        Result.objects.create(
            result_form=result_form,
            user=self.user,
            candidate=candidate1,
            votes=10,
            entry_version=EntryVersion.DATA_ENTRY_1
        )
        Result.objects.create(
            result_form=result_form,
            user=self.user,
            candidate=candidate2,
            votes=20,
            entry_version=EntryVersion.DATA_ENTRY_1
        )
        Result.objects.create(
            result_form=result_form,
            user=self.user,
            candidate=candidate1,
            votes=10,
            entry_version=EntryVersion.DATA_ENTRY_2
        )
        # Missing second DATA_ENTRY_2 result - count mismatch!

        results = result_form.results.all()

        # Should raise exception due to count mismatch
        with self.assertRaises(SuspiciousOperation) as cm:
            get_matched_results(result_form, results)

        # Verify the exception message
        self.assertIn("Unexpected number of results", str(cm.exception))

        # Reload and verify tracking
        result_form.refresh_from_db()
        self.assertEqual(result_form.previous_form_state, initial_state)
        # reject() sets form_state to DATA_ENTRY_1
        self.assertEqual(result_form.form_state, FormState.DATA_ENTRY_1)

    def test_corrections_passed_property(self):
        """Test the corrections_passed property under various conditions."""
        result_form = create_result_form(
            tally=self.tally,
            ballot=self.ballot,
            form_state=FormState.CORRECTION,
            center=self.center,
            station_number=self.station.station_number
        )
        candidate1 = create_candidate(self.ballot, "cand1", tally=self.tally)

        self.assertTrue(result_form.corrections_passed)
        Result.objects.create(result_form=result_form,
                          user=self.user,
                          candidate=candidate1,
                          votes=10,
                          entry_version=EntryVersion.DATA_ENTRY_1)
        Result.objects.create(result_form=result_form,
                          user=self.user,
                          candidate=candidate1,
                          votes=10,
                          entry_version=EntryVersion.DATA_ENTRY_2)
        self.assertTrue(result_form.corrections_passed)

        result_form.results.filter(
            candidate=candidate1,
            entry_version=EntryVersion.DATA_ENTRY_2).update(votes=11)
        self.assertFalse(result_form.corrections_passed)
        result_form.results.all().delete()

        create_reconciliation_form(
            result_form, self.user, entry_version=EntryVersion.DATA_ENTRY_1,
            number_valid_votes=50)
        create_reconciliation_form(
            result_form, self.user, entry_version=EntryVersion.DATA_ENTRY_2,
            number_valid_votes=50)
        self.assertTrue(result_form.corrections_passed)

        result_form.reconciliationform_set.filter(
            entry_version=EntryVersion.DATA_ENTRY_2
        ).update(number_valid_votes=51)
        self.assertFalse(result_form.corrections_passed)
        result_form.reconciliationform_set.all().delete()

        Result.objects.create(result_form=result_form,
                          user=self.user,
                          candidate=candidate1,
                          votes=10,
                          entry_version=EntryVersion.DATA_ENTRY_1)
        Result.objects.create(result_form=result_form,
                          user=self.user,
                          candidate=candidate1,
                          votes=10,
                          entry_version=EntryVersion.DATA_ENTRY_2)
        create_reconciliation_form(
            result_form, self.user,
            entry_version=EntryVersion.DATA_ENTRY_1,
            number_valid_votes=50)
        create_reconciliation_form(
            result_form, self.user,
            entry_version=EntryVersion.DATA_ENTRY_2,
            number_valid_votes=50)
        self.assertTrue(result_form.corrections_passed)

        result_form.results.filter(
            candidate=candidate1,
            entry_version=EntryVersion.DATA_ENTRY_2).update(votes=11)
        self.assertFalse(result_form.corrections_passed)

        result_form.results.filter(
            candidate=candidate1,
            entry_version=EntryVersion.DATA_ENTRY_2).update(votes=10)
        result_form.reconciliationform_set.filter(
            entry_version=EntryVersion.DATA_ENTRY_2).update(number_valid_votes=51)
        self.assertFalse(result_form.corrections_passed)

    def test_has_recon_property(self):
        """Test the has_recon property based on center code."""
        result_form_normal = create_result_form(
            barcode=123456789,
            tally=self.tally,
            ballot=self.ballot,
            center=self.center,
            station_number=self.station.station_number
        )
        self.assertTrue(result_form_normal.has_recon)

        ocv_center =\
            create_center(code=ResultForm.OCV_CENTER_MIN,
                          tally=self.tally,
                          sub_constituency=self.sub_constituency,
                          office_name=self.office.name)
        result_form_ocv =\
            create_result_form(
                barcode=123456790,
                tally=self.tally,
                ballot=self.ballot,
                center=ocv_center,
                station_number=1,
            serial_number=2
        )
        self.assertFalse(result_form_ocv.has_recon)

        result_form_no_center =\
            create_result_form(
                barcode=123456791,
                tally=self.tally,
                ballot=self.ballot,
                center=None,
                station_number=self.station.station_number,
            serial_number=3
        )
        self.assertFalse(result_form_no_center.has_recon)

    def test_candidates_property(self):
        """Test the candidates property retrieves candidates
        for the form's ballot.
        """
        result_form = create_result_form(
            tally=self.tally,
            ballot=self.ballot,
            center=self.center,
            station_number=self.station.station_number
        )
        candidate1 = create_candidate(self.ballot, "cand1", tally=self.tally)
        candidate2 = create_candidate(self.ballot, "cand2", tally=self.tally)

        other_ballot =\
            create_ballot(self.tally,
                          electrol_race=self.electrol_race,
                          number=2)
        create_candidate(other_ballot, "other_cand", tally=self.tally)

        self.assertListEqual(
            list(result_form.candidates), [candidate1, candidate2])

    def test_simple_properties(self):
        """Test various simple read-only properties."""
        result_form = create_result_form(
            center=self.center,
            station_number=self.station.station_number,
            ballot=self.ballot,
            tally=self.tally,
            form_state=FormState.QUALITY_CONTROL,
            gender=Gender.FEMALE
        )
        self.assertEqual(
            result_form.form_state_name, FormState.QUALITY_CONTROL.label)
        self.assertEqual(
            result_form.gender_name, _(self.station.gender.name))
        self.assertEqual(result_form.center_code, self.center.code)
        self.assertEqual(result_form.center_office, self.center.office.name)
        self.assertEqual(
            result_form.center_office_number, self.center.office.number)
        self.assertEqual(result_form.ballot_number, self.ballot.number)
        self.assertEqual(
            result_form.ballot_race_type_name,
            self.ballot.electrol_race.election_level)
        self.assertEqual(
            result_form.sub_constituency_code,
            self.sub_constituency.code)
        self.assertEqual(result_form.center_name, self.center.name)

    def test_reject_method(self):
        """Test the reject method."""
        result_form = create_result_form(
            tally=self.tally,
            ballot=self.ballot,
            form_state=FormState.QUALITY_CONTROL,
            center=self.center,
            station_number=self.station.station_number
        )
        candidate = create_candidate(self.ballot, "cand1", tally=self.tally)
        create_result(result_form, candidate, self.user, votes=10)
        res = Result.objects.get(
            result_form=result_form, candidate=candidate, user=self.user)
        recon = create_reconciliation_form(result_form, self.user)
        initial_rejected_count = result_form.rejected_count

        result_form.reject(new_state=FormState.DATA_ENTRY_1)

        result_form.refresh_from_db()
        res.refresh_from_db()
        recon.refresh_from_db()

        self.assertEqual(result_form.form_state, FormState.DATA_ENTRY_1)
        self.assertEqual(
            result_form.rejected_count, initial_rejected_count + 1)
        self.assertFalse(result_form.duplicate_reviewed)
        self.assertIsNone(result_form.reject_reason)
        self.assertFalse(res.active)
        self.assertIsNone(res.deactivated_by_request)
        self.assertFalse(recon.active)
        self.assertIsNone(recon.deactivated_by_request)

        result_form.form_state = FormState.AUDIT
        res.active = True
        recon.active = True
        res.save()
        recon.save()
        result_form.save()

        reject_reason_text = "Needs re-entry"
        workflow_request = WorkflowRequest.objects.create(
            request_type=RequestType.RECALL_FROM_ARCHIVE,
            result_form=result_form,
            requester=self.user,
            request_reason=RequestReason.OTHER,
            request_comment="Recall from audit"
        )

        result_form.reject(
            new_state=FormState.CORRECTION,
            reject_reason=reject_reason_text,
            workflow_request=workflow_request
        )

        result_form.refresh_from_db()
        res.refresh_from_db()
        recon.refresh_from_db()

        self.assertEqual(result_form.form_state, FormState.CORRECTION)
        self.assertEqual(
            result_form.rejected_count, initial_rejected_count + 2)
        self.assertEqual(result_form.reject_reason, reject_reason_text)
        self.assertFalse(res.active)
        self.assertEqual(res.deactivated_by_request, workflow_request)
        self.assertFalse(recon.active)
        self.assertEqual(recon.deactivated_by_request, workflow_request)

    def test_get_duplicated_forms_method(self):
        """Test the get_duplicated_forms method."""
        form_unsubmitted =\
            create_result_form(tally=self.tally,
                              ballot=self.ballot,
                              center=self.center,
                              station_number=self.station.station_number,
                              form_state=FormState.UNSUBMITTED,
                              barcode='bc1', serial_number=1)
        form_intake =\
            create_result_form(tally=self.tally,
                              ballot=self.ballot,
                              center=self.center,
                              station_number=self.station.station_number,
                              form_state=FormState.INTAKE,
                              barcode='bc2', serial_number=2)
        form_de1 =\
            create_result_form(tally=self.tally,
                              ballot=self.ballot,
                              center=self.center,
                              station_number=self.station.station_number,
                              form_state=FormState.DATA_ENTRY_1,
                              barcode='bc3', serial_number=3)
        form_clearance =\
            create_result_form(
                tally=self.tally,
                ballot=self.ballot,
                center=self.center,
                station_number=self.station.station_number,
                form_state=FormState.CLEARANCE,
                barcode='bc4',
                serial_number=4
            )

        duplicates = form_unsubmitted.get_duplicated_forms()
        self.assertNotIn(form_unsubmitted, duplicates)
        self.assertIn(form_intake, duplicates)
        self.assertIn(form_de1, duplicates)
        self.assertIn(form_clearance, duplicates)

        duplicates = form_intake.get_duplicated_forms()
        self.assertNotIn(form_unsubmitted, duplicates)
        self.assertNotIn(form_intake, duplicates)
        self.assertIn(form_de1, duplicates)
        self.assertIn(form_clearance, duplicates)

        duplicates = form_de1.get_duplicated_forms()
        self.assertEqual(len(duplicates), 0)

        duplicates = form_clearance.get_duplicated_forms()
        self.assertNotIn(form_unsubmitted, duplicates)
        self.assertIn(form_intake, duplicates)
        self.assertIn(form_de1, duplicates)
        self.assertIn(form_clearance, duplicates)

    def test_send_to_clearance_method(self):
        """Test the send_to_clearance method."""
        result_form = create_result_form(
            tally=self.tally,
            ballot=self.ballot,
            form_state=FormState.INTAKE,
            center=self.center,
            station_number=self.station.station_number
        )
        audit =\
            create_audit(result_form, self.user)

        initial_state = result_form.form_state
        result_form.send_to_clearance()

        result_form.refresh_from_db()
        audit.refresh_from_db()

        self.assertEqual(result_form.form_state, FormState.CLEARANCE)
        self.assertEqual(result_form.previous_form_state, initial_state)
        self.assertFalse(audit.active)

    def test_generate_barcode_classmethod(self):
        """Test the generate_barcode class method."""
        initial_barcode =\
            ResultForm.generate_barcode(tally_id=self.tally.id)
        self.assertEqual(initial_barcode, ResultForm.START_BARCODE + 1)

        create_result_form(
            tally=self.tally,
            ballot=self.ballot,
            barcode=str(initial_barcode),
            center=self.center,
            station_number=self.station.station_number
        )

        next_barcode = ResultForm.generate_barcode(tally_id=self.tally.id)
        self.assertEqual(next_barcode, initial_barcode + 1)

        other_tally = create_tally(name="OtherTally")
        other_barcode = ResultForm.generate_barcode(tally_id=other_tally.id)
        self.assertEqual(other_barcode, ResultForm.START_BARCODE + 1)

    def test_forms_in_state_classmethod(self):
        """Test the forms_in_state class method."""
        form_de1 =\
            create_result_form(tally=self.tally, ballot=self.ballot,
                              form_state=FormState.DATA_ENTRY_1,
                              center=self.center,
                              station_number=self.station.station_number,
                              barcode='state1')

        station2 =\
            Station.objects.create(
                center=self.center,
                station_number=self.station.station_number + 1,
                registrants=100,
                gender=Gender.MALE,
                sub_constituency=self.sub_constituency,
            tally=self.tally
        )

        form_de2 =\
            create_result_form(tally=self.tally, ballot=self.ballot,
                              form_state=FormState.DATA_ENTRY_2,
                              center=self.center,
                              station_number=station2.station_number,
                              barcode='state2', serial_number=2)

        create_result_form(tally=self.tally, ballot=self.ballot,
                              form_state=FormState.DATA_ENTRY_1,
                              center=self.center,
                              station_number=self.station.station_number,
                              barcode='state3', is_replacement=True,
                              serial_number=3)

        forms_in_de1 =\
            ResultForm.forms_in_state(FormState.DATA_ENTRY_1,
                                      tally_id=self.tally.id)

        distinct_pks = ResultForm.distinct_form_pks(tally_id=self.tally.id)
        expected_form_pks = [form_de1.pk, form_de2.pk]
        self.assertCountEqual(list(distinct_pks), expected_form_pks)

        self.assertIn(
            form_de1.pk, list(forms_in_de1.values_list('pk', flat=True)))
        self.assertNotIn(
            form_de2.pk, list(forms_in_de1.values_list('pk', flat=True)))

        forms_in_de2 =\
            ResultForm.forms_in_state(FormState.DATA_ENTRY_2,
                                      tally_id=self.tally.id)
        self.assertCountEqual(
            list(forms_in_de2.values_list('pk', flat=True)), [form_de2.pk])

    def test_get_pending_intake_for_station(self):
        """Test the get_pending_intake_for_station class method."""
        # Form in the correct state for the target station
        pending_form = create_result_form(
            tally=self.tally,
            ballot=self.ballot,
            center=self.center,
            station_number=self.station.station_number,
            form_state=FormState.UNSUBMITTED,
            barcode='123456789',
        )
        # Form in a different state for the target station
        create_result_form(
            tally=self.tally,
            ballot=self.ballot,
            center=self.center,
            station_number=self.station.station_number,
            form_state=FormState.INTAKE,
            barcode='123456790',
            serial_number=2
        )
        # Form in the correct state but for a different station
        station2 =\
            create_station(
                self.center,
                tally=self.tally,
                station_number=self.station.station_number + 1
            )
        create_result_form(
            tally=self.tally,
            ballot=self.ballot,
            center=self.center,
            station_number=station2.station_number,
            form_state=FormState.UNSUBMITTED,
            barcode='123456791',
            serial_number=3
        )

        pending_qs = ResultForm.get_pending_intake_for_station(
            self.tally.id, self.center.code, self.station.station_number
        )
        self.assertQuerySetEqual(
            pending_qs, [pending_form], transform=lambda x: x)

        pending_qs_no_center = ResultForm.get_pending_intake_for_station(
            self.tally.id, None, self.station.station_number
        )
        self.assertFalse(pending_qs_no_center.exists())

        pending_qs_no_station = ResultForm.get_pending_intake_for_station(
            self.tally.id, self.center.code, None
        )
        self.assertFalse(pending_qs_no_station.exists())

        pending_qs_bad_station = ResultForm.get_pending_intake_for_station(
            self.tally.id, self.center.code, 9999
        )
        self.assertFalse(pending_qs_bad_station.exists())

    def test_get_intaken_for_station(self):
        """Test the get_intaken_for_station class method."""
        intaken_states = [
            FormState.DATA_ENTRY_1,
            FormState.DATA_ENTRY_2,
            FormState.CORRECTION,
            FormState.QUALITY_CONTROL,
            FormState.ARCHIVED,
            FormState.AUDIT
        ]
        intaken_forms = []
        for i, state in enumerate(intaken_states):
            form = create_result_form(
                tally=self.tally,
                ballot=self.ballot,
                center=self.center,
                station_number=self.station.station_number,
                form_state=state,
                barcode=f'12345679{i}',
                serial_number=i + 1
            )
            intaken_forms.append(form)

        create_result_form(
            tally=self.tally,
            ballot=self.ballot,
            center=self.center,
            station_number=self.station.station_number,
            form_state=FormState.UNSUBMITTED,
            barcode='123456799',
            serial_number=len(intaken_states) + 1
        )
        station2 =\
            create_station(
                self.center,
                tally=self.tally,
                station_number=self.station.station_number + 1
            )
        create_result_form(
            tally=self.tally,
            ballot=self.ballot,
            center=self.center,
            station_number=station2.station_number,
            form_state=FormState.DATA_ENTRY_1,
            barcode='123456800',
            serial_number=len(intaken_states) + 2
        )

        intaken_qs = ResultForm.get_intaken_for_station(
            self.tally.id, self.center.code, self.station.station_number
        )
        self.assertCountEqual(list(intaken_qs), intaken_forms)

        intaken_qs_no_center = ResultForm.get_intaken_for_station(
            self.tally.id, None, self.station.station_number
        )
        self.assertFalse(intaken_qs_no_center.exists())

        intaken_qs_no_station = ResultForm.get_intaken_for_station(
            self.tally.id, self.center.code, None
        )
        self.assertFalse(intaken_qs_no_station.exists())

        intaken_qs_bad_station = ResultForm.get_intaken_for_station(
            self.tally.id, self.center.code, 9999
        )
        self.assertFalse(intaken_qs_bad_station.exists())

    def test_get_pending_intake_for_center(self):
        """Test the get_pending_intake_for_center class method."""
        station2 =\
            create_station(
                self.center,
                tally=self.tally,
                station_number=self.station.station_number + 1
            )
        ballot2 =\
            create_ballot(
                self.tally,
                electrol_race=self.electrol_race,
                number=2
            )

        pending_form_s1_b1 =\
            create_result_form(
                tally=self.tally, ballot=self.ballot, center=self.center,
                station_number=self.station.station_number,
                form_state=FormState.UNSUBMITTED,
                barcode='123456801',
                serial_number=1
            )
        pending_form_s1_b2 =\
            create_result_form(
                tally=self.tally, ballot=ballot2, center=self.center,
                station_number=self.station.station_number,
                form_state=FormState.UNSUBMITTED,
                barcode='123456802',
                serial_number=2
            )
        pending_form_s2_b1 =\
            create_result_form(
                tally=self.tally, ballot=self.ballot, center=self.center,
                station_number=station2.station_number,
                form_state=FormState.UNSUBMITTED,
                barcode='123456803',
                serial_number=3
            )
        create_result_form(
            tally=self.tally, ballot=self.ballot, center=self.center,
            station_number=self.station.station_number,
            form_state=FormState.INTAKE,
            barcode='123456804', serial_number=4
        )
        center2 =\
            create_center(code=self.center.code + 1, tally=self.tally,
                          sub_constituency=self.sub_constituency,
                          office_name=self.office.name)
        station_c2 =\
            create_station(center2, tally=self.tally)
        create_result_form(
            tally=self.tally, ballot=self.ballot, center=center2,
            station_number=station_c2.station_number,
            form_state=FormState.UNSUBMITTED,
            barcode='123456805', serial_number=5
        )

        pending_qs = ResultForm.get_pending_intake_for_center(
            self.tally.id, self.center.code
        )
        expected_order =\
            [pending_form_s1_b1, pending_form_s1_b2, pending_form_s2_b1]
        self.assertQuerySetEqual(
            pending_qs, expected_order, transform=lambda x: x)

        pending_qs_no_center = ResultForm.get_pending_intake_for_center(
            self.tally.id, None
        )
        self.assertFalse(pending_qs_no_center.exists())

        # Test non-existent center
        pending_qs_bad_center = ResultForm.get_pending_intake_for_center(
            self.tally.id, 99999
        )
        self.assertFalse(pending_qs_bad_center.exists())

    def test_get_intaken_for_center(self):
        """Test the get_intaken_for_center class method."""
        station2 =\
            create_station(
                self.center,
                tally=self.tally,
                station_number=self.station.station_number + 1
            )
        ballot2 =\
            create_ballot(
                self.tally, electrol_race=self.electrol_race, number=2)
        intaken_forms = []
        serial_counter = 1

        form_s1_b1_de1 =\
            create_result_form(
                tally=self.tally, ballot=self.ballot, center=self.center,
                station_number=self.station.station_number,
                form_state=FormState.DATA_ENTRY_1,
                barcode='123456806', serial_number=serial_counter
            )
        serial_counter += 1
        intaken_forms.append(form_s1_b1_de1)
        form_s1_b2_qc =\
            create_result_form(
                tally=self.tally, ballot=ballot2, center=self.center,
                station_number=self.station.station_number,
                form_state=FormState.QUALITY_CONTROL,
                barcode='123456807', serial_number=serial_counter
            )
        serial_counter += 1
        intaken_forms.append(form_s1_b2_qc)

        form_s2_b1_arch =\
            create_result_form(
                tally=self.tally,
                ballot=self.ballot,
                center=self.center,
                station_number=station2.station_number,
                form_state=FormState.ARCHIVED,
                barcode='123456808', serial_number=serial_counter
            )
        serial_counter += 1
        intaken_forms.append(form_s2_b1_arch)

        create_result_form(
            tally=self.tally, ballot=self.ballot, center=self.center,
            station_number=self.station.station_number,
            form_state=FormState.UNSUBMITTED,
            barcode='123456809', serial_number=serial_counter
        )
        serial_counter += 1

        center2 =\
            create_center(code=self.center.code + 1, tally=self.tally,
                          sub_constituency=self.sub_constituency,
                          office_name=self.office.name)
        station_c2 =\
            create_station(center2, tally=self.tally)
        create_result_form(
            tally=self.tally,
            ballot=self.ballot,
            center=center2,
            station_number=station_c2.station_number,
            form_state=FormState.DATA_ENTRY_1,
            barcode='123456810', serial_number=serial_counter)
        serial_counter += 1

        intaken_qs = ResultForm.get_intaken_for_center(
            self.tally.id, self.center.code
        )
        expected_order =\
            [form_s1_b1_de1, form_s1_b2_qc, form_s2_b1_arch]
        self.assertQuerySetEqual(
            intaken_qs, expected_order, transform=lambda x: x)
        self.assertCountEqual(list(intaken_qs), intaken_forms)

        intaken_qs_no_center = ResultForm.get_intaken_for_center(
            self.tally.id, None
        )
        self.assertFalse(intaken_qs_no_center.exists())

        intaken_qs_bad_center = ResultForm.get_intaken_for_center(
            self.tally.id, 99999
        )
        self.assertFalse(intaken_qs_bad_center.exists())

    def test_reset_to_unsubmitted_sets_state(self):
        """Test reset_to_unsubmitted() sets form state to UNSUBMITTED."""
        result_form = create_result_form(
            tally=self.tally,
            ballot=self.ballot,
            center=self.center,
            station_number=self.station.station_number,
            form_state=FormState.ARCHIVED
        )

        self.assertEqual(result_form.form_state, FormState.ARCHIVED)

        reason = "Test reason for reset"
        result_form.reset_to_unsubmitted(user=self.user, reason=reason)

        self.assertEqual(result_form.form_state, FormState.UNSUBMITTED)

    def test_reset_to_unsubmitted_deactivates_results(self):
        """Test reset_to_unsubmitted() deactivates all Result records."""
        result_form = create_result_form(
            tally=self.tally,
            ballot=self.ballot,
            center=self.center,
            station_number=self.station.station_number,
            form_state=FormState.QUALITY_CONTROL
        )
        candidate = create_candidate(self.ballot, "cand1", tally=self.tally)

        result1 = create_result(result_form, candidate, self.user, votes=10)
        result2 = Result.objects.create(
            result_form=result_form,
            user=self.user,
            candidate=candidate,
            votes=15,
            entry_version=EntryVersion.DATA_ENTRY_1
        )

        self.assertTrue(result1.active)
        self.assertTrue(result2.active)

        reason = "Test reason for reset"
        result_form.reset_to_unsubmitted(user=self.user, reason=reason)

        result1.refresh_from_db()
        result2.refresh_from_db()

        self.assertFalse(result1.active)
        self.assertFalse(result2.active)
        self.assertEqual(result_form.form_state, FormState.UNSUBMITTED)

    def test_reset_to_unsubmitted_deactivates_reconciliation_forms(self):
        """Test reset_to_unsubmitted() deactivates
        ReconciliationForm records."""
        result_form = create_result_form(
            tally=self.tally,
            ballot=self.ballot,
            center=self.center,
            station_number=self.station.station_number,
            form_state=FormState.DATA_ENTRY_2
        )

        recon1 = create_reconciliation_form(
            result_form, self.user, entry_version=EntryVersion.DATA_ENTRY_1
        )
        recon2 = create_reconciliation_form(
            result_form, self.user, entry_version=EntryVersion.DATA_ENTRY_2
        )

        self.assertTrue(recon1.active)
        self.assertTrue(recon2.active)

        reason = "Test reason for reset"
        result_form.reset_to_unsubmitted(user=self.user, reason=reason)

        recon1.refresh_from_db()
        recon2.refresh_from_db()

        self.assertFalse(recon1.active)
        self.assertFalse(recon2.active)
        self.assertEqual(result_form.form_state, FormState.UNSUBMITTED)

    def test_reset_to_unsubmitted_deactivates_audits(self):
        """Test reset_to_unsubmitted() deactivates Audit records."""
        result_form = create_result_form(
            tally=self.tally,
            ballot=self.ballot,
            center=self.center,
            station_number=self.station.station_number,
            form_state=FormState.AUDIT
        )

        audit = create_audit(result_form, self.user)
        self.assertTrue(audit.active)

        reason = "Test reason for reset"
        result_form.reset_to_unsubmitted(user=self.user, reason=reason)

        audit.refresh_from_db()
        self.assertFalse(audit.active)
        self.assertEqual(result_form.form_state, FormState.UNSUBMITTED)

    def test_reset_to_unsubmitted_deactivates_clearances(self):
        """Test reset_to_unsubmitted() deactivates Clearance records."""
        result_form = create_result_form(
            tally=self.tally,
            ballot=self.ballot,
            center=self.center,
            station_number=self.station.station_number,
            form_state=FormState.CLEARANCE
        )

        clearance = create_clearance(result_form, self.user)
        self.assertTrue(clearance.active)

        reason = "Test reason for reset"
        result_form.reset_to_unsubmitted(user=self.user, reason=reason)

        clearance.refresh_from_db()
        self.assertFalse(clearance.active)
        self.assertEqual(result_form.form_state, FormState.UNSUBMITTED)

    def test_reset_to_unsubmitted_deactivates_quality_control(self):
        """Test reset_to_unsubmitted() deactivates QualityControl records."""
        result_form = create_result_form(
            tally=self.tally,
            ballot=self.ballot,
            center=self.center,
            station_number=self.station.station_number,
            form_state=FormState.QUALITY_CONTROL
        )

        qc = QualityControl.objects.create(
            result_form=result_form, user=self.user, active=True
        )
        self.assertTrue(qc.active)

        reason = "Test reason for reset"
        result_form.reset_to_unsubmitted(user=self.user, reason=reason)

        qc.refresh_from_db()
        self.assertFalse(qc.active)
        self.assertEqual(result_form.form_state, FormState.UNSUBMITTED)

    def test_reset_to_unsubmitted_deactivates_archives(self):
        """Test reset_to_unsubmitted() deactivates Archive records."""
        result_form = create_result_form(
            tally=self.tally,
            ballot=self.ballot,
            center=self.center,
            station_number=self.station.station_number,
            form_state=FormState.ARCHIVED
        )

        archive1 = Archive.objects.create(
            result_form=result_form, tally=self.tally, user=self.user
        )
        archive2 = Archive.objects.create(
            result_form=result_form, tally=self.tally, user=self.user
        )

        self.assertTrue(archive1.active)
        self.assertTrue(archive2.active)

        reason = "Test reason for reset"
        result_form.reset_to_unsubmitted(user=self.user, reason=reason)

        archive1.refresh_from_db()
        archive2.refresh_from_db()

        self.assertFalse(archive1.active)
        self.assertFalse(archive2.active)
        self.assertEqual(result_form.form_state, FormState.UNSUBMITTED)

    def test_reset_to_unsubmitted_deactivates_all_related_records(self):
        """Test reset_to_unsubmitted() deactivates all related records."""
        result_form = create_result_form(
            tally=self.tally,
            ballot=self.ballot,
            center=self.center,
            station_number=self.station.station_number,
            form_state=FormState.ARCHIVED
        )

        candidate = create_candidate(self.ballot, "cand1", tally=self.tally)
        result = create_result(result_form, candidate, self.user, votes=10)
        recon = create_reconciliation_form(result_form, self.user)
        audit = create_audit(result_form, self.user)
        clearance = create_clearance(result_form, self.user)
        qc = QualityControl.objects.create(
            result_form=result_form, user=self.user, active=True
        )
        archive = Archive.objects.create(
            result_form=result_form, tally=self.tally, user=self.user
        )

        # Verify all are active
        self.assertTrue(result.active)
        self.assertTrue(recon.active)
        self.assertTrue(audit.active)
        self.assertTrue(clearance.active)
        self.assertTrue(qc.active)
        self.assertTrue(archive.active)

        reason = "Test reason for reset"
        result_form.reset_to_unsubmitted(user=self.user, reason=reason)

        # Refresh all from database
        result.refresh_from_db()
        recon.refresh_from_db()
        audit.refresh_from_db()
        clearance.refresh_from_db()
        qc.refresh_from_db()
        archive.refresh_from_db()

        # Verify all are now inactive
        self.assertFalse(result.active)
        self.assertFalse(recon.active)
        self.assertFalse(audit.active)
        self.assertFalse(clearance.active)
        self.assertFalse(qc.active)
        self.assertFalse(archive.active)

        # Verify form state is UNSUBMITTED
        self.assertEqual(result_form.form_state, FormState.UNSUBMITTED)

    def test_reset_to_unsubmitted_from_various_states(self):
        """Test reset_to_unsubmitted() works from various form states."""
        states_to_test = [
            FormState.INTAKE,
            FormState.DATA_ENTRY_1,
            FormState.DATA_ENTRY_2,
            FormState.CORRECTION,
            FormState.QUALITY_CONTROL,
            FormState.AUDIT,
            FormState.CLEARANCE,
            FormState.ARCHIVED
        ]

        for state in states_to_test:
            with self.subTest(state=state):
                result_form = create_result_form(
                    tally=self.tally,
                    ballot=self.ballot,
                    center=self.center,
                    station_number=self.station.station_number,
                    form_state=state,
                    barcode=f'test{state.value}',
                    serial_number=state.value
                )

                self.assertEqual(result_form.form_state, state)

                reason = "Test reason for reset"
                result_form.reset_to_unsubmitted(user=self.user, reason=reason)

                self.assertEqual(result_form.form_state, FormState.UNSUBMITTED)

    def test_reset_to_unsubmitted_with_no_related_records(self):
        """Test reset_to_unsubmitted() works when no related records exist."""
        result_form = create_result_form(
            tally=self.tally,
            ballot=self.ballot,
            center=self.center,
            station_number=self.station.station_number,
            form_state=FormState.INTAKE
        )

        # No related records created
        self.assertEqual(result_form.results.count(), 0)
        self.assertEqual(result_form.reconciliationform_set.count(), 0)
        self.assertEqual(result_form.audit_set.count(), 0)

        # Should not raise an error
        reason = "Test reason for reset"
        result_form.reset_to_unsubmitted(user=self.user, reason=reason)

        self.assertEqual(result_form.form_state, FormState.UNSUBMITTED)
