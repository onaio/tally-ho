import time

from intake_barcodes import INTAKE_CODES
from locust import HttpUser, TaskSet, task


class UserLogin(TaskSet):
    barcode = None
    barcode_placeholder = None
    barcode_copy = None
    tally_id = None
    result_form_id = None

    def on_start(self):
        self.login()

        if len(INTAKE_CODES) > 0:
            self.barcode, self.barcode_placeholder, self.barcode_copy,\
                self.tally_id, self.result_form_id = INTAKE_CODES.pop()

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
    def enter_barcode(self):
        response = self.client.get(
            f'/intake/center-details/{self.tally_id}/',
            name="Get Enter Barcode CSRF")
        csrftoken = response.cookies['csrftoken']
        self.client.post(f"/intake/center-details/{self.tally_id}/",
                         {'barcode': self.barcode,
                          'barcode_placeholder': self.barcode_placeholder,
                          'barcode_copy': self.barcode_copy,
                          'barcode_scan': '',
                          'submit': '',
                          'tally_id': self.tally_id,
                          'csrfmiddlewaretoken': csrftoken})
        response = self.client.get(
            f'/intake/check-center-details/{self.tally_id}/',
            name="Get Form State CSRF")
        csrftoken = response.cookies['csrftoken']
        self.client.post(f"/intake/check-center-details/{self.tally_id}/",
                         {
                            'result_form': self.result_form_id,
                            'is_match': 'true',
                            'match_submit': '',
                            'csrfmiddlewaretoken': csrftoken
                        })
        response = self.client.get(
            f'/intake/printcover/{self.tally_id}/',
            name="Get Intaken CSRF")
        csrftoken = response.cookies['csrftoken']
        self.client.post(f"/intake/printcover/{self.tally_id}/",
                         {'csrfmiddlewaretoken': csrftoken,
                          'submit_cover_form': '',
                          'result_form': self.result_form_id})
        while True:
            time.sleep(1)

    def on_stop(self):
        self.client.get("/accounts/logout", name="Logout")


class WebsiteUser(HttpUser):
    tasks = [UserLogin]
    host = "https://tallyho.onalabs.org"
