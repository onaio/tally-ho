from django.core.exceptions import ValidationError

from tally_ho.apps.tally.models.audit import Audit
from tally_ho.apps.tally.models.clearance import Clearance
from tally_ho.apps.tally.models.quality_control import QualityControl
from tally_ho.libs.tests.test_base import (
    TestBase,
    create_result_form,
    create_tally,
)


class TestUniqueActiveAuditConstraint(TestBase):
    def setUp(self):
        self._create_and_login_user()

    def test_second_active_audit_raises_validation_error(self):
        """Creating two active audits for the same result form raises
        ValidationError from save()."""
        tally = create_tally()
        result_form = create_result_form(tally=tally)
        Audit.objects.create(result_form=result_form, user=self.user)
        with self.assertRaises(ValidationError):
            Audit.objects.create(result_form=result_form, user=self.user)

    def test_new_active_audit_after_deactivating_existing(self):
        """After deactivating the existing audit, a new active one can be
        created."""
        tally = create_tally()
        result_form = create_result_form(tally=tally)
        audit1 = Audit.objects.create(
            result_form=result_form, user=self.user)
        audit1.active = False
        audit1.save()
        audit2 = Audit.objects.create(
            result_form=result_form, user=self.user)
        self.assertTrue(audit2.active)
        self.assertIsNotNone(audit2.pk)

    def test_multiple_inactive_audits_allowed(self):
        """Multiple inactive audits for the same result form are allowed."""
        tally = create_tally()
        result_form = create_result_form(tally=tally)
        a1 = Audit.objects.create(
            result_form=result_form, user=self.user)
        a1.active = False
        a1.save()
        a2 = Audit.objects.create(
            result_form=result_form, user=self.user)
        a2.active = False
        a2.save()
        self.assertEqual(
            result_form.audit_set.filter(active=False).count(), 2
        )

    def test_different_result_forms_each_have_active_audit(self):
        """Different result forms can each have their own active audit."""
        tally = create_tally()
        rf1 = create_result_form(tally=tally)
        rf2 = create_result_form(
            tally=tally, barcode="987654321", serial_number=1)
        a1 = Audit.objects.create(result_form=rf1, user=self.user)
        a2 = Audit.objects.create(result_form=rf2, user=self.user)
        self.assertTrue(a1.active)
        self.assertTrue(a2.active)


class TestUniqueActiveQualityControlConstraint(TestBase):
    def setUp(self):
        self._create_and_login_user()

    def test_second_active_qc_raises_validation_error(self):
        tally = create_tally()
        result_form = create_result_form(tally=tally)
        QualityControl.objects.create(
            result_form=result_form, user=self.user
        )
        with self.assertRaises(ValidationError):
            QualityControl.objects.create(
                result_form=result_form, user=self.user
            )

    def test_new_active_qc_after_deactivating_existing(self):
        tally = create_tally()
        result_form = create_result_form(tally=tally)
        qc1 = QualityControl.objects.create(
            result_form=result_form, user=self.user
        )
        qc1.active = False
        qc1.save()
        qc2 = QualityControl.objects.create(
            result_form=result_form, user=self.user
        )
        self.assertTrue(qc2.active)
        self.assertIsNotNone(qc2.pk)

    def test_multiple_inactive_qc_allowed(self):
        tally = create_tally()
        result_form = create_result_form(tally=tally)
        qc1 = QualityControl.objects.create(
            result_form=result_form, user=self.user
        )
        qc1.active = False
        qc1.save()
        qc2 = QualityControl.objects.create(
            result_form=result_form, user=self.user
        )
        qc2.active = False
        qc2.save()
        self.assertEqual(
            result_form.qualitycontrol_set.filter(active=False).count(), 2
        )


class TestUniqueActiveClearanceConstraint(TestBase):
    def setUp(self):
        self._create_and_login_user()

    def test_second_active_clearance_raises_validation_error(self):
        tally = create_tally()
        result_form = create_result_form(tally=tally)
        Clearance.objects.create(
            result_form=result_form, user=self.user
        )
        with self.assertRaises(ValidationError):
            Clearance.objects.create(
                result_form=result_form, user=self.user
            )

    def test_new_active_clearance_after_deactivating_existing(self):
        tally = create_tally()
        result_form = create_result_form(tally=tally)
        c1 = Clearance.objects.create(
            result_form=result_form, user=self.user
        )
        c1.active = False
        c1.save()
        c2 = Clearance.objects.create(
            result_form=result_form, user=self.user
        )
        self.assertTrue(c2.active)
        self.assertIsNotNone(c2.pk)

    def test_multiple_inactive_clearances_allowed(self):
        tally = create_tally()
        result_form = create_result_form(tally=tally)
        c1 = Clearance.objects.create(
            result_form=result_form, user=self.user
        )
        c1.active = False
        c1.save()
        c2 = Clearance.objects.create(
            result_form=result_form, user=self.user
        )
        c2.active = False
        c2.save()
        self.assertEqual(
            result_form.clearances.filter(active=False).count(), 2
        )
