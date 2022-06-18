import pytest

from analyzer.utils.testing import import_batches
from tests.api.test_imports import IMPORT_BATCHES, ROOT_ID


@pytest.mark.asyncio
async def test_delete(client):
    await import_batches(client, IMPORT_BATCHES, 200)

    response = await client.delete(f"/delete/{ROOT_ID}")
    assert response.status_code == 200

    response = await client.delete(f"/delete/{ROOT_ID}")
    assert response.status_code == 404
