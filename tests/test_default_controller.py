# coding: utf-8

import pytest
import json
from aiohttp import web

from openapi_server.models.pipeline import Pipeline


async def test_add_pipeline(client):
    """Test case for add_pipeline

    Creates a pipeline.
    """
    body = {
  "sqa_criteria" : [ "", "" ],
  "run" : true
}
    headers = { 
        'Content-Type': 'application/json',
    }
    response = await client.request(
        method='POST',
        path='/v1/pipeline',
        headers=headers,
        json=body,
        )
    assert response.status == 200, 'Response body is : ' + (await response.read()).decode('utf-8')

