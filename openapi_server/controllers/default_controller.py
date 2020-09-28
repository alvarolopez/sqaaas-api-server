from typing import List, Dict
from aiohttp import web

from openapi_server.models.pipeline import Pipeline
from openapi_server import util


async def add_pipeline(request: web.Request, body) -> web.Response:
    """Creates a pipeline.

    Provides a ready-to-use Jenkins pipeline based on the v2 series of jenkins-pipeline-library. 

    :param body: 
    :type body: dict | bytes

    """
    body = Pipeline.from_dict(body)
    return web.Response(status=200)


async def get_pipeline_by_id(request: web.Request, pipeline_id) -> web.Response:
    """Find pipeline by ID

    

    :param pipeline_id: ID of the pipeline to get
    :type pipeline_id: int

    """
    return web.Response(status=200)
