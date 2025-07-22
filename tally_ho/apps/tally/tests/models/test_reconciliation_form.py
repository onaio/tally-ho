from tally_ho.libs.tests.test_base import (
    TestBase,
    create_candidates,
    create_reconciliation_form,
    create_result_form,
)


class TestReconciliationForm(TestBase):
    num_used = 1

    def setUp(self):
        self._create_and_login_user()

    def test_number_ballots_used_no_results(self):
        """Test number of ballots used with no results"""
        result_form = create_result_form()
        re_form = create_reconciliation_form(result_form, self.user)

        self.assertEqual(re_form.number_ballots_used, self.num_used)

    def test_number_ballots_used_results(self):
        """Test number of ballots used is correct"""
        expected_votes = 0

        for num_results in range(1, 4):
            for votes in range(1, 4):
                result_form = create_result_form()
                create_candidates(
                    result_form,
                    self.user,
                    votes=votes,
                    num_results=num_results,
                )
                re_form = create_reconciliation_form(result_form, self.user)

                expected_votes += num_results * votes * 2

                self.assertEqual(
                    re_form.number_ballots_used, self.num_used + expected_votes
                )
