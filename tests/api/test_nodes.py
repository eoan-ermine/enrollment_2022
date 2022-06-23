from uuid import uuid4

import pytest

from analyzer.utils.testing import (
    assert_nodes_response,
    assert_response,
    import_batches,
)
from tests.api.test_imports import IMPORT_BATCHES, ROOT_ID


@pytest.mark.asyncio
async def test_nodes_category(client):
    expected_tree = {
        "type": "CATEGORY",
        "name": "Товары",
        "id": "069cb8d7-bbdd-47d3-ad8f-82ef4c269df1",
        "price": None,
        "parentId": None,
        "date": "2022-02-01T12:00:00Z",
        "children": [],
    }

    await import_batches(client, IMPORT_BATCHES[:1], 200)

    assert_nodes_response(await client.get(f"/nodes/{ROOT_ID}"), 200, expected_tree)


@pytest.mark.asyncio
async def test_nodes_offer(client):
    item_id = "73bc3b36-02d1-4245-ab35-3106c9ee1c65"
    batches = [
        {
            "items": [
                {
                    "type": "OFFER",
                    "name": 'Goldstar 65" LED UHD LOL Very Smart',
                    "id": item_id,
                    "parentId": None,
                    "price": 69999,
                }
            ],
            "updateDate": "2022-02-02T12:00:00Z",
        }
    ]
    expected_tree = {
        "type": "OFFER",
        "name": 'Goldstar 65" LED UHD LOL Very Smart',
        "id": item_id,
        "parentId": None,
        "date": "2022-02-02T12:00:00Z",
        "price": 69999,
        "children": None,
    }

    await import_batches(client, batches, 200)

    assert_nodes_response(await client.get(f"/nodes/{item_id}"), 200, expected_tree)


@pytest.mark.asyncio
async def test_nodes_not_found(client):
    random_uuid = str(uuid4())

    assert_response(await client.get(f"/nodes/{random_uuid}"), 404)


@pytest.mark.asyncio
async def test_delete_invalid(client):
    assert_response(await client.get("/nodes/invalid_uuid"), 400)
    assert_response(await client.get("/nodes/12345"), 400)
