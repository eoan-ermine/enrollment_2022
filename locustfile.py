from datetime import datetime, timedelta
from random import choice

from locust import HttpUser, constant, task

from analyzer.utils.testing import generate_shop_unit, random_date

DATETIME_ENCODER = lambda d: "%04d" % d.year + d.strftime("-%m-%dT%H:%M:%SZ")
CATEGORY_DEPTH_LIMIT = 30


class ImportUser(HttpUser):
    wait_time = constant(1)

    @task
    def import_unit(self):
        offer_unit = generate_shop_unit(is_category=False, parent_id=choice(self.category_ids))
        self.request(
            "POST", "/imports", 200, json={"items": [offer_unit], "updateDate": DATETIME_ENCODER(self.current_date)}
        )
        self.current_date = self.current_date + timedelta(days=1)

    def on_start(self):
        root_unit = generate_shop_unit(is_category=True)

        parent_id, categories = root_unit["id"], [root_unit]
        for _ in range(CATEGORY_DEPTH_LIMIT - 1):
            category = generate_shop_unit(is_category=True, parent_id=parent_id)
            categories.append(category)
            parent_id = category["id"]

        self.current_date = random_date(datetime(year=2000, month=1, day=1), datetime(year=3000, month=1, day=1))
        self.category_ids = [category["id"] for category in categories]

        self.request(
            "POST", "/imports", 200, json={"items": categories, "updateDate": DATETIME_ENCODER(self.current_date)}
        )

    def request(self, method, path, expected_result, **kwargs):
        with self.client.request(method, path, catch_response=True, **kwargs) as resp:
            if resp.status_code != expected_result:
                resp.failure(f"expected status {expected_result}, got {resp.status_code}")
        return resp
