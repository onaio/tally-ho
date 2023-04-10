# Performance Tests

Runs the code on locust.io in a browser.

1. `locust -f data_entry1_clerk.py`

Runs the code in the terminal, `-u` specifies number of users, `-r` is for ramp up time.

2. `locust -f data_entry1_clerk.py --headless -u 2 -r 6`
