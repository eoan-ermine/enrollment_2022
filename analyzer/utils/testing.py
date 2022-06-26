import json
import os
import random
import string
import subprocess
from datetime import timedelta
from typing import Dict, List, Optional, Tuple
from uuid import uuid4

from httpx import AsyncClient, Response

from analyzer.api.schema import ShopUnitImportRequest


def deep_sort(node, key):
    if node.get(key):
        node[key].sort(key=lambda x: x["id"])

        for child in node[key]:
            deep_sort(child, key)


def print_diff(expected, response):
    with open("expected.json", "w") as f:
        json.dump(expected, f, indent=2, ensure_ascii=False, sort_keys=True)
        f.write("\n")

    with open("response.json", "w") as f:
        json.dump(response, f, indent=2, ensure_ascii=False, sort_keys=True)
        f.write("\n")

    completed_process = subprocess.run(
        ["git", "--no-pager", "diff", "--no-index", "expected.json", "response.json"], capture_output=True
    )
    os.remove("expected.json")
    os.remove("response.json")
    return completed_process.stdout


def compare_result(lhs, rhs, sort_key=None):
    if sort_key:
        deep_sort(lhs, sort_key)
        deep_sort(rhs, sort_key)

    import json

    left = json.dumps(lhs, indent=2, sort_keys=True)
    right = json.dumps(rhs, indent=2, sort_keys=True)

    import difflib

    diff = difflib.unified_diff(left.splitlines(True), right.splitlines(True), fromfile="left", tofile="right")
    assert lhs == rhs, "\n" + "".join(diff)


def compare_nodes(lhs, rhs):
    compare_result(lhs, rhs, "children")


def compare_statistics(lhs, rhs):
    lhs["items"] = sorted(lhs["items"], key=lambda x: x["price"])
    rhs["items"] = sorted(rhs["items"], key=lambda x: x["price"])
    compare_result(lhs, rhs)


async def import_batches(client: AsyncClient, batches: List[ShopUnitImportRequest], expected_status: int):
    for i, batch in enumerate(batches):
        response = await client.post("/imports", json=batch)
        assert (
            response.status_code == expected_status
        ), f"{i} BATCH FAILED, expected {expected_status} got {response.status_code}"


def expected_statistics(info: List[Tuple[str, str, str, str, str, int]]):
    return {
        "items": [
            {
                "type": unit_type,
                "name": name,
                "id": unit_id,
                "parentId": parent_id,
                "date": date,
                "price": price,
            }
            for unit_type, name, unit_id, parent_id, date, price in info
        ]
    }


def assert_response(response: Response, status_code: int):
    assert response.status_code == status_code


async def assert_nodes(client: AsyncClient, node_id: str, status_code: int, expected_result: Dict):
    response = await client.get(f"/nodes/{node_id}")
    assert_response(response, status_code)
    compare_nodes(response.json(), expected_result)


def assert_statistics_response(response: Response, status_code: int, expected_result: Dict):
    assert_response(response, status_code)
    compare_statistics(response.json(), expected_result)


async def assert_statistics(
    client: AsyncClient, node_id: str, status_code: int, expected_result: Dict, *args, **kwargs
):
    response = await client.get(f"/node/{node_id}/statistic", *args, **kwargs)
    assert_statistics_response(response, status_code, expected_result)


async def assert_sales(client, status_code: int, expected_result: Dict, *args, **kwargs):
    response = await client.get("/sales", *args, **kwargs)
    assert_statistics_response(response, status_code, expected_result)


def random_string(length: int):
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=length))


def random_date(start, end):
    delta = end - start
    int_delta = (delta.days * 24 * 60 * 60) + delta.seconds
    random_second = random.randrange(int_delta)
    return start + timedelta(seconds=random_second)


def generate_shop_unit(is_category: bool, parent_id: Optional[str] = None) -> Dict:
    return {
        "type": "CATEGORY" if is_category else "OFFER",
        "name": random_string(random.randint(5, 50)),
        "id": str(uuid4()),
        "parentId": parent_id if parent_id else None,
        "price": random.randint(100, 1000000) if not is_category else None,
    }
