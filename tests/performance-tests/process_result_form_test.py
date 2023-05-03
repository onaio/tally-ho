from locust import HttpUser, TaskSet, task
from data import RESULT_FORMS_DATA, RESULTS
import time


class UserLogin(TaskSet):
    barcode = None
    place_holder = None
    barcode_copy = None
    tally_id = None
    result_form_id = None
    center_code = None
    station_number = None

    def on_start(self):
        self.login()

        if len(RESULT_FORMS_DATA) > 0:
            self.barcode, self.place_holder, self.barcode_copy,\
                self.tally_id, self.result_form_id, self.center_code,\
                self.station_number = RESULT_FORMS_DATA.pop()

    def login(self):
        response = self.client.get('/accounts/login/', name="Get CSRF")
        self.client.headers['Referer'] = self.client.base_url
        csrftoken = response.cookies['csrftoken']
        self.client.post("/accounts/login/",
                         {'username': 'intake_clerk',
                          'password': 'data',
                          'csrfmiddlewaretoken': csrftoken,
                          'next': '/'})

    @task(5)
    def process_result_form(self):
        # Fill barcode
        response = self.client.get(
            '/intake/center-details/{}/'.format(self.tally_id),
            name="Get Enter Barcode page CSRF")
        csrftoken = response.cookies['csrftoken']
        self.client.post("/intake/center-details/{}/".format(self.tally_id),
                         {'barcode': self.barcode,
                          'barcode_placeholder': self.place_holder,
                          'barcode_copy': self.barcode_copy,
                          'barcode_scan': '',
                          'submit': '',
                          'tally_id': self.tally_id,
                          'csrfmiddlewaretoken': csrftoken
                          })
        # Confirm Center and Station Details
        response = self.client.get(
            '/intake/check-center-details/{}/'.format(self.tally_id),
            name="Get check center and station details page CSRF")
        csrftoken = response.cookies['csrftoken']
        self.client.post("/intake/check-center-details/{}/".format(
            self.tally_id),
                         {
                            'result_form': self.result_form_id,
                            'is_match': 'true',
                            'match_submit': '',
                            'csrfmiddlewaretoken': csrftoken
                        })
        # Print cover
        response = self.client.get(
            '/intake/printcover/{}/'.format(self.tally_id),
            name="Get CSRF for Print Cover Letter page")
        csrftoken = response.cookies['csrftoken']
        self.client.post("/intake/printcover/{}/".format(self.tally_id),
                         {'csrfmiddlewaretoken': csrftoken,
                          'submit_cover_form': '',
                          'result_form': self.result_form_id})
        # Logout User
        self.client.get("/accounts/logout", name="Logout Intake Clerk")
        time.sleep(20)

        # Login data entry 1 clerk
        response = self.client.get(
            '/accounts/login/', name="Get login page CSRF")
        self.client.headers['Referer'] = self.client.base_url
        csrftoken = response.cookies['csrftoken']
        self.client.post("/accounts/login/",
                         {'username': 'data_entry_1_clerk',
                          'password': 'data',
                          'csrfmiddlewaretoken': csrftoken,
                          'next': '/'})
        # Fill barcode
        response = self.client.get(
            '/data-entry/{}/'.format(self.tally_id),
            name="Get Enter Barcode page CSRF")
        csrftoken = response.cookies['csrftoken']
        self.client.post("/data-entry/{}/".format(self.tally_id),
                         {'barcode': self.barcode,
                          'barcode_placeholder': self.place_holder,
                          'barcode_copy': self.barcode_copy,
                          'barcode_scan': '',
                          'submit': '',
                          'tally_id': self.tally_id,
                          'csrfmiddlewaretoken': csrftoken})
        # Fill Center and Station details
        response = self.client.get(
            '/data-entry/enter-center-details/{}/'.format(self.tally_id),
            name="Get Center and Station details page CSRF")
        csrf_token = response.cookies['csrftoken']
        self.client.post("/data-entry/enter-center-details/{}/".format(
            self.tally_id),
                         {'result_form': self.result_form_id,
                          'center_number': self.center_code,
                          'center_number_placeholder': self.place_holder,
                          'center_number_copy': self.center_code,
                          'station_number': self.station_number,
                          'station_number_placeholder': self.place_holder,
                          'station_number_copy': self.station_number,
                          'submit': '',
                          'tally_id': self.tally_id,
                          'csrfmiddlewaretoken': csrf_token})
        # Fill results
        response = self.client.get(
            '/data-entry/enter-results/{}/'.format(self.tally_id),
            name="Get results page CSRF")
        csrf_token = response.cookies['csrftoken']
        RESULTS['result_form'] = self.result_form_id,
        RESULTS['csrfmiddlewaretoken'] = csrf_token
        self.client.post("/data-entry/enter-results/{}/".format(self.tally_id),
                         RESULTS)
        # Logout User
        self.client.get("/accounts/logout", name="Logout Data Entry 1 Clerk")
        time.sleep(20)

        # Login data entry 2 clerk
        response = self.client.get(
            '/accounts/login/', name="Get login page CSRF")
        self.client.headers['Referer'] = self.client.base_url
        csrftoken = response.cookies['csrftoken']
        self.client.post("/accounts/login/",
                         {'username': 'data_entry_2_clerk',
                          'password': 'data',
                          'csrfmiddlewaretoken': csrftoken,
                          'next': '/'})
        # Fill barcode
        response = self.client.get(
            '/data-entry/{}/'.format(self.tally_id),
            name="Get Enter Barcode page CSRF")
        csrftoken = response.cookies['csrftoken']
        self.client.post("/data-entry/{}/".format(self.tally_id),
                         {'barcode': self.barcode,
                          'barcode_placeholder': self.place_holder,
                          'barcode_copy': self.barcode_copy,
                          'barcode_scan': '',
                          'submit': '',
                          'tally_id': self.tally_id,
                          'csrfmiddlewaretoken': csrftoken})
        # Fill Center and Station details
        response = self.client.get(
            '/data-entry/enter-center-details/{}/'.format(self.tally_id),
            name="Get Center and Station details page CSRF")
        csrf_token = response.cookies['csrftoken']
        self.client.post("/data-entry/enter-center-details/{}/".format(
            self.tally_id),
                         {'result_form': self.result_form_id,
                          'center_number': self.center_code,
                          'center_number_placeholder': self.place_holder,
                          'center_number_copy': self.center_code,
                          'station_number': self.station_number,
                          'station_number_placeholder': self.place_holder,
                          'station_number_copy': self.station_number,
                          'submit': '',
                          'tally_id': self.tally_id,
                          'csrfmiddlewaretoken': csrf_token})
        # Fill results
        response = self.client.get(
            '/data-entry/enter-results/{}/'.format(self.tally_id),
            name="Get results page CSRF")
        csrf_token = response.cookies['csrftoken']
        RESULTS['result_form'] = self.result_form_id,
        RESULTS['csrfmiddlewaretoken'] = csrf_token
        self.client.post("/data-entry/enter-results/{}/".format(self.tally_id),
                         RESULTS)
        # Logout User
        self.client.get("/accounts/logout", name="Logout Data Entry 2 Clerk")
        time.sleep(10)

        # Login corrections clerk
        response = self.client.get(
            '/accounts/login/', name="Get login page CSRF")
        self.client.headers['Referer'] = self.client.base_url
        csrftoken = response.cookies['csrftoken']
        self.client.post("/accounts/login/",
                         {'username': 'corrections_clerk',
                          'password': 'data',
                          'csrfmiddlewaretoken': csrftoken,
                          'next': '/'})
        # Fill barcode
        response = self.client.get(
            '/corrections/{}/'.format(self.tally_id),
            name="GET Reconciliation Form Page CSRF   ")
        csrftoken = response.cookies['csrftoken']
        self.client.post("/corrections/{}/".format(self.tally_id),
                         {'barcode': self.barcode,
                          'barcode_placeholder': self.place_holder,
                          'barcode_copy': self.barcode_copy,
                          'barcode_scan': '',
                          'submit': '',
                          'tally_id': self.tally_id,
                          'csrfmiddlewaretoken': csrftoken})
        # Submit corrections details
        response = self.client.get(
            '/corrections/required/{}/'.format(self.tally_id),
            name="Get Corrections Page")
        csrf_token = response.cookies['csrftoken']
        self.client.post("/corrections/required/{}/".format(self.tally_id),
                         {'result_form': self.result_form_id,
                          'submit_corrections': 'submit corrections',
                          'csrfmiddlewaretoken': csrf_token})
        # Logout User
        self.client.get("/accounts/logout", name="Logout Corrections Clerk")
        time.sleep(20)

        # Login quality control clerk
        response = self.client.get(
            '/accounts/login/', name="Get login page CSRF")
        self.client.headers['Referer'] = self.client.base_url
        csrftoken = response.cookies['csrftoken']
        self.client.post("/accounts/login/",
                         {'username': 'quality_control_clerk',
                          'password': 'data',
                          'csrfmiddlewaretoken': csrftoken,
                          'next': '/'})
        # Fill barcode
        response = self.client.get(
            '/quality-control/home/{}/'.format(self.tally_id),
            name="GET Quality Control Page CSRF")
        csrftoken = response.cookies['csrftoken']
        self.client.post("/quality-control/home/{}/".format(self.tally_id),
                         {'barcode': self.barcode,
                          'barcode_placeholder': self.place_holder,
                          'barcode_copy': self.barcode_copy,
                          'barcode_scan': '',
                          'submit': '',
                          'tally_id': self.tally_id,
                          'csrfmiddlewaretoken': csrftoken})
        # Review Reconciliation details
        response = self.client.get(
            '/quality-control/dashboard/{}/'.format(self.tally_id),
            name="Get Reconciliation Page")
        csrf_token = response.cookies['csrftoken']
        self.client.post("/quality-control/dashboard/{}/".format(
            self.tally_id),
                         {'result_form': self.result_form_id,
                          'correct': '',
                          'csrfmiddlewaretoken': csrf_token})
        # Submit Quality Control Form
        response = self.client.get(
            '/quality-control/print/{}/'.format(self.tally_id),
            name="Get Print Page")
        csrf_token = response.cookies['csrftoken']
        self.client.post("/quality-control/print/{}/".format(self.tally_id),
                         {'result_form': self.result_form_id,
                          'submit_cover_form': '',
                          'csrfmiddlewaretoken': csrf_token})
        while True:
            time.sleep(1)

    def on_stop(self):
        self.client.get("/accounts/logout", name="Logout")


class WebsiteUser(HttpUser):
    tasks = [UserLogin]
    host = "https://tallyho.onalabs.org"
