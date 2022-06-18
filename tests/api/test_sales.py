import pytest

from analyzer.utils.testing import import_batches
from tests.api.test_imports import IMPORT_BATCHES


@pytest.mark.asyncio
async def test_sales(client):
    await import_batches(client, IMPORT_BATCHES, 200)

    response = await client.get("/sales", params={"date": "2022-02-04T00:00:00Z"})
    assert response.status_code == 200
