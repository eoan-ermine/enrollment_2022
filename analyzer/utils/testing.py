import json
import os
import subprocess
from typing import List

from httpx import AsyncClient

from analyzer.api.schema import ShopUnitImportRequest


def deep_sort_children(node):
    if node.get("children"):
        node["children"].sort(key=lambda x: x["id"])

        for child in node["children"]:
            deep_sort_children(child)


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


def compare_nodes(lhs, rhs):
    deep_sort_children(lhs)
    deep_sort_children(rhs)

    import json

    left = json.dumps(lhs, indent=2, sort_keys=True)
    right = json.dumps(rhs, indent=2, sort_keys=True)

    import difflib

    diff = difflib.unified_diff(left.splitlines(True), right.splitlines(True), fromfile="left", tofile="right")
    assert lhs == rhs, "\n" + "".join(diff)


async def import_batches(client: AsyncClient, batches: List[ShopUnitImportRequest], expected_status: int):
    for i, batch in enumerate(batches):
        response = await client.post("/imports", json=batch)
        assert (
            response.status_code == expected_status
        ), f"{i} BATCH FAILED, expected {expected_status} got {response.status_code}"
