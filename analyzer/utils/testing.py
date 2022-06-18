from typing import List

from httpx import AsyncClient

from analyzer.api.schema import ShopUnitImportRequest


def deep_sort_children(node):
    if node.get("children"):
        node["children"].sort(key=lambda x: x["id"])

        for child in node["children"]:
            deep_sort_children(child)


def compare_nodes(lhs, rhs):
    deep_sort_children(lhs)
    deep_sort_children(rhs)
    return lhs == rhs


async def import_batches(client: AsyncClient, batches: List[ShopUnitImportRequest], expected_status: int):
    for i, batch in enumerate(batches):
        response = await client.post("/imports", json=batch)
        assert response.status_code == expected_status, f"{i} BATCH FAILED"
