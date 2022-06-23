from datetime import datetime, timedelta
from typing import List, Tuple
from uuid import uuid4

import pytest
from pydantic.json import ENCODERS_BY_TYPE

from analyzer.utils.testing import (
    compare_statistics,
    expected_statistics,
    import_batches,
)
from tests.api.test_imports import IMPORT_BATCHES, ROOT_ID


@pytest.mark.asyncio
async def test_stats(client):
    await import_batches(client, IMPORT_BATCHES, 200)

    response = await client.get(
        f"/node/{ROOT_ID}/statistic", params={"dateStart": "2022-02-01T00:00:00Z", "dateEnd": "2022-02-03T00:00:00Z"}
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_stats_corner_dates(client):
    node_id = "73bc3b36-02d1-4245-ab35-3106c9ee1c65"
    expected_tree = {
        "items": [
            {
                "type": "OFFER",
                "name": 'Goldstar 65" LED UHD LOL Very Smart',
                "id": node_id,
                "parentId": "1cc0129a-2bfe-474c-9ee6-d435bf5fc8f2",
                "date": "2022-02-03T15:00:00Z",
                "price": 69999,
            }
        ]
    }

    await import_batches(client, IMPORT_BATCHES, 200)

    begin_corner_response = await client.get(
        f"/node/{node_id}/statistic", params={"dateStart": "2022-02-03T15:00:00Z", "dateEnd": "2022-02-03T16:00:00Z"}
    )
    assert begin_corner_response.status_code == 200
    compare_statistics(begin_corner_response.json(), expected_tree)

    end_corner_response = await client.get(
        f"/node/{node_id}/statistic", params={"dateStart": "2022-02-03T14:00:00Z", "dateEnd": "2022-02-03T15:00:00Z"}
    )
    assert end_corner_response.status_code == 200
    compare_statistics(end_corner_response.json(), {"items": []})

    end_corner_response = await client.get(
        f"/node/{node_id}/statistic", params={"dateStart": "2022-02-03T14:00:00Z", "dateEnd": "2022-02-03T15:00:01Z"}
    )
    assert end_corner_response.status_code == 200
    compare_statistics(end_corner_response.json(), expected_tree)


@pytest.mark.asyncio
async def test_stats_not_found(client):
    random_uuid = str(uuid4())

    response = await client.get(f"/node/{random_uuid}/statistic")
    assert response.status_code == 404


@pytest.mark.asyncio
async def tests_stats_omit_borders(client):
    node_id = "73bc3b36-02d1-4245-ab35-3106c9ee1c65"

    datetime_min = ENCODERS_BY_TYPE[datetime](datetime.min)
    datetime_max = ENCODERS_BY_TYPE[datetime](datetime.max - timedelta(seconds=1))

    batches = [
        {
            "items": [
                {
                    "type": "OFFER",
                    "name": 'Goldstar 65" LED UHD LOL Very Smart',
                    "id": node_id,
                    "parentId": None,
                    "price": 1000,
                }
            ],
            "updateDate": datetime_min,
        },
        {
            "items": [
                {
                    "type": "OFFER",
                    "name": 'Goldstar 65" LED UHD LOL Very Smart',
                    "id": node_id,
                    "parentId": None,
                    "price": 100000,
                }
            ],
            "updateDate": datetime_max,
        },
    ]

    def expected_unit_statistics(info: List[Tuple[str, int]]):
        return expected_statistics(
            [
                (
                    "OFFER",
                    'Goldstar 65" LED UHD LOL Very Smart',
                    node_id,
                    None,
                    date,
                    price,
                )
                for date, price in info
            ]
        )

    await import_batches(client, batches, 200)

    response = await client.get(f"/node/{node_id}/statistic", params={"dateEnd": "2022-02-03T15:00:00Z"})
    assert response.status_code == 200
    compare_statistics(response.json(), expected_unit_statistics([(datetime_min, 1000)]))

    response = await client.get(f"/node/{node_id}/statistic", params={"dateStart": "2022-02-03T15:00:00Z"})
    assert response.status_code == 200
    compare_statistics(response.json(), expected_unit_statistics([(datetime_max, 100000)]))

    response = await client.get(f"/node/{node_id}/statistic")
    assert response.status_code == 200
    compare_statistics(response.json(), expected_unit_statistics([(datetime_min, 1000), (datetime_max, 100000)]))


@pytest.mark.asyncio
async def test_stats_incorrect_date(client):
    await import_batches(client, IMPORT_BATCHES, 200)

    response = await client.get(
        f"/node/{ROOT_ID}/statistic", params={"dateStart": "2022-02-03T15:00:00Z", "dateEnd": "2022-02-03T15:00:00Z"}
    )
    assert response.status_code == 400

    response = await client.get(
        f"/node/{ROOT_ID}/statistic", params={"dateStart": "2022-02-03T16:00:00Z", "dateEnd": "2022-02-03T15:00:00Z"}
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def tests_stats_rfc_3339(client):
    await import_batches(client, IMPORT_BATCHES, 200)

    # Valid dates

    response = await client.get(f"/node/{ROOT_ID}/statistic", params={"dateStart": "2022-06-23T03:35:17+00:00"})
    assert response.status_code == 200

    response = await client.get(f"/node/{ROOT_ID}/statistic", params={"dateStart": "2022-06-23T03:35:17Z"})
    assert response.status_code == 200

    # Invalid dates

    # Нет time-offset
    response = await client.get(f"/node/{ROOT_ID}/statistic", params={"dateStart": "2022-06-23T03:35:17"})
    assert response.status_code == 400

    # Нет разделителей (удовлетворяет ISO 8601, но не RFC3339)
    response = await client.get(f"/node/{ROOT_ID}/statistic", params={"dateStart": "20220623T033517Z"})
    assert response.status_code == 400


@pytest.mark.asyncio
async def tests_stats_categories(client):
    SMARTPHONES_ID = "d515e43f-f3f6-4471-bb77-6b455017a2d2"
    TVS_ID = "1cc0129a-2bfe-474c-9ee6-d435bf5fc8f2"

    def expected_smartphones_statistics(info: List[Tuple[str, int]]):
        return expected_statistics(
            [
                (
                    "CATEGORY",
                    "Смартфоны",
                    "d515e43f-f3f6-4471-bb77-6b455017a2d2",
                    "069cb8d7-bbdd-47d3-ad8f-82ef4c269df1",
                    date,
                    price,
                )
                for date, price in info
            ]
        )

    def expected_tvs_statistics(info: List[Tuple[str, int]]):
        return expected_statistics(
            [
                (
                    "CATEGORY",
                    "Телевизоры",
                    "1cc0129a-2bfe-474c-9ee6-d435bf5fc8f2",
                    "069cb8d7-bbdd-47d3-ad8f-82ef4c269df1",
                    date,
                    price,
                )
                for date, price in info
            ]
        )

    def expected_goods_statistics(info: List[Tuple[str, int]]):
        return expected_statistics(
            [("CATEGORY", "Товары", "069cb8d7-bbdd-47d3-ad8f-82ef4c269df1", None, date, price) for date, price in info]
        )

    await import_batches(client, IMPORT_BATCHES, 200)

    response = await client.get(f"/node/{SMARTPHONES_ID}/statistic")
    assert response.status_code == 200
    compare_statistics(response.json(), expected_smartphones_statistics([("2022-02-02T12:00:00Z", 69999)]))

    response = await client.get(f"/node/{TVS_ID}/statistic")
    assert response.status_code == 200
    compare_statistics(
        response.json(), expected_tvs_statistics([("2022-02-03T12:00:00Z", 41499), ("2022-02-03T15:00:00Z", 50999)])
    )

    response = await client.get(f"/node/{ROOT_ID}/statistic")
    assert response.status_code == 200
    compare_statistics(
        response.json(),
        expected_goods_statistics(
            [("2022-02-02T12:00:00Z", 69999), ("2022-02-03T12:00:00Z", 55749), ("2022-02-03T15:00:00Z", 58599)]
        ),
    )
