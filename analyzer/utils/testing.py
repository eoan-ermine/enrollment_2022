import json
import os
import subprocess
from typing import Dict, List, Tuple

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


def assert_nodes_response(response: Response, status_code: int, expected_result: Dict):
    assert_response(response, status_code)
    compare_nodes(response.json(), expected_result)


def assert_statistics_response(response: Response, status_code: int, expected_result: Dict):
    assert_response(response, status_code)
    compare_statistics(response.json(), expected_result)
