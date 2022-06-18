import pytest

from analyzer.utils.testing import import_batches
from tests.api.test_imports import IMPORT_BATCHES, ROOT_ID


@pytest.mark.asyncio
async def test_stats(client):
    await import_batches(client, IMPORT_BATCHES, 200)

    response = await client.get(
        f"/node/{ROOT_ID}/statistic", params={"dateStart": "2022-02-01T00:00:00Z", "dateEnd": "2022-02-03T00:00:00Z"}
    )
    assert response.status_code == 200
