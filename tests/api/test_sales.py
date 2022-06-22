import pytest

from analyzer.utils.testing import compare_statistics, import_batches
from tests.api.test_imports import IMPORT_BATCHES


@pytest.mark.asyncio
async def test_sales(client):
    await import_batches(client, IMPORT_BATCHES, 200)

    response = await client.get("/sales", params={"date": "2022-02-04T00:00:00Z"})
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_sales_corner_dates(client):
    expected_tree_end_corner = {
        "items": [
            {
                "type": "OFFER",
                "name": 'Samson 70" LED UHD Smart',
                "id": "98883e8f-0507-482f-bce2-2fb306cf6483",
                "parentId": "1cc0129a-2bfe-474c-9ee6-d435bf5fc8f2",
                "date": "2022-02-03T12:00:00Z",
                "price": 32999,
            },
            {
                "type": "OFFER",
                "name": 'Phyllis 50" LED UHD Smarter',
                "id": "74b81fda-9cdc-4b63-8927-c978afed5cf4",
                "parentId": "1cc0129a-2bfe-474c-9ee6-d435bf5fc8f2",
                "date": "2022-02-03T12:00:00Z",
                "price": 49999,
            },
            {
                "type": "OFFER",
                "name": 'Goldstar 65" LED UHD LOL Very Smart',
                "id": "73bc3b36-02d1-4245-ab35-3106c9ee1c65",
                "parentId": "1cc0129a-2bfe-474c-9ee6-d435bf5fc8f2",
                "date": "2022-02-03T15:00:00Z",
                "price": 69999,
            },
        ]
    }

    expected_tree_begin_corner = {
        "items": [
            {
                "type": "OFFER",
                "name": 'Goldstar 65" LED UHD LOL Very Smart',
                "id": "73bc3b36-02d1-4245-ab35-3106c9ee1c65",
                "parentId": "1cc0129a-2bfe-474c-9ee6-d435bf5fc8f2",
                "date": "2022-02-03T15:00:00Z",
                "price": 69999,
            }
        ]
    }

    await import_batches(client, IMPORT_BATCHES, 200)

    end_corner_response = await client.get("/sales", params={"date": "2022-02-03T15:00:00Z"})
    assert end_corner_response.status_code == 200
    compare_statistics(end_corner_response.json(), expected_tree_end_corner)

    begin_corner_response = await client.get("/sales", params={"date": "2022-02-04T15:00:00Z"})
    assert begin_corner_response.status_code == 200
    compare_statistics(begin_corner_response.json(), expected_tree_begin_corner)


@pytest.mark.asyncio
async def test_sales_update(client):
    batches = [
        {
            "items": [
                {
                    "type": "OFFER",
                    "name": 'Goldstar 65" LED UHD LOL Very Smart',
                    "id": "73bc3b36-02d1-4245-ab35-3106c9ee1c65",
                    "parentId": "1cc0129a-2bfe-474c-9ee6-d435bf5fc8f2",
                    "price": 79999,
                }
            ],
            "updateDate": "2022-02-03T16:00:00Z",
        }
    ]

    expected_tree = {
        "items": [
            {
                "type": "OFFER",
                "name": 'Goldstar 65" LED UHD LOL Very Smart',
                "id": "73bc3b36-02d1-4245-ab35-3106c9ee1c65",
                "parentId": "1cc0129a-2bfe-474c-9ee6-d435bf5fc8f2",
                "date": "2022-02-03T15:00:00Z",
                "price": 69999,
            },
            {
                "type": "OFFER",
                "name": 'Goldstar 65" LED UHD LOL Very Smart',
                "id": "73bc3b36-02d1-4245-ab35-3106c9ee1c65",
                "parentId": "1cc0129a-2bfe-474c-9ee6-d435bf5fc8f2",
                "date": "2022-02-03T16:00:00Z",
                "price": 79999,
            },
        ]
    }

    await import_batches(client, IMPORT_BATCHES, 200)
    await import_batches(client, batches, 200)

    response = await client.get("/sales", params={"date": "2022-02-04T15:00:00Z"})
    assert response.status_code == 200
    compare_statistics(response.json(), expected_tree)


@pytest.mark.asyncio
async def test_sales_delete(client):
    unit_id = "73bc3b36-02d1-4245-ab35-3106c9ee1c65"
    batches = [
        {
            "items": [{"type": "OFFER", "name": "Товар", "id": unit_id, "price": 999}],
            "updateDate": "2022-02-03T15:00:00Z",
        }
    ]
    expected_tree = {"items": []}

    await import_batches(client, batches, 200)

    response = await client.delete(f"/delete/{unit_id}")
    assert response.status_code == 200

    response = await client.get("/sales", params={"date": "2022-02-04T15:00:00Z"})
    assert response.status_code == 200
    compare_statistics(response.json(), expected_tree)
