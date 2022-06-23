import pytest

from analyzer.utils.testing import (
    assert_nodes_response,
    assert_response,
    assert_statistics_response,
    import_batches,
)
from tests.api.test_imports import IMPORT_BATCHES, ROOT_ID


@pytest.mark.asyncio
async def test_delete(client):
    await import_batches(client, IMPORT_BATCHES, 200)

    assert_response(await client.delete(f"/delete/{ROOT_ID}"), 200)
    assert_response(await client.delete(f"/delete/{ROOT_ID}"), 404)


@pytest.mark.asyncio
async def test_delete_category_item(client):
    category_id = "1cc0129a-2bfe-474c-9ee6-d435bf5fc8f2"
    item_id = "73bc3b36-02d1-4245-ab35-3106c9ee1c65"
    expected_tree = {
        "type": "CATEGORY",
        "name": "Телевизоры",
        "id": "1cc0129a-2bfe-474c-9ee6-d435bf5fc8f2",
        "parentId": "069cb8d7-bbdd-47d3-ad8f-82ef4c269df1",
        "date": "2022-02-03T15:00:00Z",
        "price": 41499,
        "children": [
            {
                "type": "OFFER",
                "name": 'Samson 70" LED UHD Smart',
                "id": "98883e8f-0507-482f-bce2-2fb306cf6483",
                "parentId": "1cc0129a-2bfe-474c-9ee6-d435bf5fc8f2",
                "date": "2022-02-03T12:00:00Z",
                "price": 32999,
                "children": None,
            },
            {
                "type": "OFFER",
                "name": 'Phyllis 50" LED UHD Smarter',
                "id": "74b81fda-9cdc-4b63-8927-c978afed5cf4",
                "parentId": "1cc0129a-2bfe-474c-9ee6-d435bf5fc8f2",
                "date": "2022-02-03T12:00:00Z",
                "price": 49999,
                "children": None,
            },
        ],
    }

    await import_batches(client, IMPORT_BATCHES, 200)

    assert_response(await client.delete(f"/delete/{item_id}"), 200)
    assert_nodes_response(await client.get(f"/nodes/{category_id}"), 200, expected_tree)


@pytest.mark.asyncio
async def test_delete_category(client):
    category_id = "1cc0129a-2bfe-474c-9ee6-d435bf5fc8f2"
    items_ids = [
        "98883e8f-0507-482f-bce2-2fb306cf6483",
        "74b81fda-9cdc-4b63-8927-c978afed5cf4",
        "73bc3b36-02d1-4245-ab35-3106c9ee1c65",
    ]

    expected_tree = {
        "type": "CATEGORY",
        "name": "Товары",
        "id": "069cb8d7-bbdd-47d3-ad8f-82ef4c269df1",
        "price": 69999,
        "parentId": None,
        "date": "2022-02-03T15:00:00Z",
        "children": [
            {
                "type": "CATEGORY",
                "name": "Смартфоны",
                "id": "d515e43f-f3f6-4471-bb77-6b455017a2d2",
                "parentId": "069cb8d7-bbdd-47d3-ad8f-82ef4c269df1",
                "price": 69999,
                "date": "2022-02-02T12:00:00Z",
                "children": [
                    {
                        "type": "OFFER",
                        "name": "jPhone 13",
                        "id": "863e1a7a-1304-42ae-943b-179184c077e3",
                        "parentId": "d515e43f-f3f6-4471-bb77-6b455017a2d2",
                        "price": 79999,
                        "date": "2022-02-02T12:00:00Z",
                        "children": None,
                    },
                    {
                        "type": "OFFER",
                        "name": "Xomiа Readme 10",
                        "id": "b1d8fd7d-2ae3-47d5-b2f9-0f094af800d4",
                        "parentId": "d515e43f-f3f6-4471-bb77-6b455017a2d2",
                        "price": 59999,
                        "date": "2022-02-02T12:00:00Z",
                        "children": None,
                    },
                ],
            },
        ],
    }

    await import_batches(client, IMPORT_BATCHES, 200)

    assert_response(await client.delete(f"/delete/{category_id}"), 200)
    assert_nodes_response(await client.get(f"/nodes/{ROOT_ID}"), 200, expected_tree)

    for item_id in items_ids:
        assert_response(await client.get(f"/nodes/{item_id}"), 404)


@pytest.mark.asyncio
async def test_delete_history(client):
    await import_batches(client, IMPORT_BATCHES, 200)

    assert_response(await client.delete(f"/delete/{ROOT_ID}"), 200)
    assert_statistics_response(await client.get("/sales", params={"date": "2022-02-03T15:00:00Z"}), 200, {"items": []})
