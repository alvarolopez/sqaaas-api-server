import shelve
import uuid

from typing import List, Dict
from aiohttp import web

from openapi_server.models.pipeline import Pipeline
from openapi_server import util


DB_FILE = 'sqaaas.shelve'


def load_db_content():
    return shelve.open(DB_FILE)


def store_db_content(d):
    with shelve.open(DB_FILE) as db:
        db = d
        print('### Pipeline DB ##')
        for k in db.keys():
            print(k, db[k])
        print('##################')


async def add_pipeline(request: web.Request, body) -> web.Response:
    """Creates a pipeline.

    Provides a ready-to-use Jenkins pipeline based on the v2 series of jenkins-pipeline-library.

    :param body:
    :type body: dict | bytes

    """
    pipeline_id = str(uuid.uuid4())
    body = Pipeline.from_dict(body)
    db = load_db_content()
    db[pipeline_id] = {'sqa_criteria': body.sqa_criteria}
    store_db_content(db)

    return web.Response(status=200)


async def get_pipeline_by_id(request: web.Request, pipeline_id) -> web.Response:
    """Find pipeline by ID

    

    :param pipeline_id: ID of the pipeline to get
    :type pipeline_id: int

    """
    return web.Response(status=200)
