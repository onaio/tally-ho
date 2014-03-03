from tally_system.libs.tests.test_base import create_candidates,\
    create_reconciliation_form, create_result_form, TestBase


class TestReconciliationForm(TestBase):
    num_used = 3

    def setUp(self):
        self._create_and_login_user()

    def test_number_ballots_used_no_results(self):
        result_form = create_result_form()
        re_form = create_reconciliation_form(result_form, self.user)

        self.assertEqual(re_form.number_ballots_used, self.num_used)

    def test_number_ballots_used_results(self):
        expected_votes = 0

        for num_results in xrange(1, 4):
            for votes in xrange(1, 4):
                result_form = create_result_form()
                create_candidates(result_form, self.user, votes=votes,
                                  num_results=num_results)
                re_form = create_reconciliation_form(result_form, self.user)

                expected_votes += num_results * votes * 2

                self.assertEqual(re_form.number_ballots_used,
                                 self.num_used + expected_votes)
