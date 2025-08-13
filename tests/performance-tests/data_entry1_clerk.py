import time

from center_details import CENTER_DETAILS
from intake_barcodes import INTAKE_CODES
from locust import HttpUser, TaskSet, task


class UserLogin(TaskSet):
    barcode = None
    placeholder = None
    barcode_copy = None
    tally_id = None
    result_form_id = None
    center_number = None
    center_number_copy = None
    station_number = None
    station_number_copy = None
    result_form = None

    def on_start(self):
        self.login()

        if len(INTAKE_CODES) > 0:
            self.barcode, self.placeholder, self.barcode_copy, \
                self.tally_id, self.result_form_id = INTAKE_CODES.pop()

        if len(CENTER_DETAILS) > 0:
            self.center_number, self.placeholder, self.center_number_copy, \
                self.station_number, self.station_number_copy, \
                self.result_form = CENTER_DETAILS.pop()

    def login(self):
        response = self.client.get('/accounts/login/', name="Get CSRF")
        self.client.headers['Referer'] = self.client.base_url
        csrftoken = response.cookies['csrftoken']
        self.client.post("/accounts/login/",
                         {'username': 'data_entry_1_clerk',
                          'password': 'data',
                          'csrfmiddlewaretoken': csrftoken,
                          'next': '/'})

    @task(5)
    def enter_barcode(self):
        response = self.client.get(
            f'/data-entry/{self.tally_id}/',
            name="Get Enter Barcode CSRF")
        csrftoken = response.cookies['csrftoken']
        self.client.post(f"/data-entry/{self.tally_id}/",
                         {'barcode': self.barcode,
                          'barcode_placeholder': self.placeholder,
                          'barcode_copy': self.barcode_copy,
                          'barcode_scan': '',
                          'submit': '',
                          'tally_id': self.tally_id,
                          'csrfmiddlewaretoken': csrftoken})
        response = self.client.get(
            f'/data-entry/enter-center-details/{self.tally_id}/',
            name="Get Center Details CSRF")
        csrftoken = response.cookies['csrftoken']
        self.client.post(f"/data-entry/enter-center-details/{self.tally_id}/",
                         {'result-form': self.result_form,
                          'center_number': self.center_number,
                          'center-number-placeholder': self.placeholder,
                          'center-number-copy': self.center_number_copy,
                          'station-number': self.station_number,
                          'station-number-placeholder': self.placeholder,
                          'station-number-copy': self.station_number_copy,
                          'tally_id': self.tally_id,
                          'submit': '',
                          'csrfmiddlewaretoken': csrftoken})
        response = self.client.get(
            f'/data-entry/enter-results/{self.tally_id}/',
            name="Get Results CSRF")
        csrftoken = response.cookies['csrftoken']
        payload =\
            {
                'ballot_number_from': '1',
                'ballot_number_to': '100',
                'number_of_voters': '100',
                'number_invalid_votes': '5',
                'number_valid_votes': '7',
                'number_sorted_and_counted': '80',
                'number_of_voter_cards_in_the_ballot_box': '80',
                'form-TOTAL_FORMS': '8',
                'form-INITIAL_FORMS': '0',
                'form-MIN_NUM_FORMS': '0',
                'form-MAX_NUM_FORMS': '1000',
                'form-0-votes': '20',
                'form-1-votes': '10',
                'form-2-votes': '5',
                'form-3-votes': '2',
                'form-4-votes': '15',
                'form-5-votes': '3',
                'form-6-votes': '7',
                'form-7-votes': '8',
                'result_form': self.result_form,
                'submit': '',
                'csrfmiddlewaretoken': csrftoken
            }
        self.client.post(f"/data-entry/enter-results/{self.tally_id}/",
                         payload)
        while True:
            time.sleep(1)

    def on_stop(self):
        self.client.get("/accounts/logout", name="Logout")


class WebsiteUser(HttpUser):
    tasks = [UserLogin]
    host = "https://tallyho.onalabs.org"
