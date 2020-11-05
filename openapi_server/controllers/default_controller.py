import json
import os
import uuid

from typing import List, Dict
from aiohttp import web

from openapi_server.models.pipeline import Pipeline
from openapi_server import util
from openapi_server.controllers.github import GitHubUtils
from openapi_server.controllers.jepl import JePLUtils


DB_FILE = 'sqaaas.json'


def load_db_content():
    data = {}
    if os.path.exists(DB_FILE) and os.stat(DB_FILE).st_size > 0:
        with open(DB_FILE) as db:
            data = json.load(db)
    return data


def store_db_content(data):
    with open(DB_FILE, 'w') as db:
        json.dump(data, db)
    print_db_content()


def print_db_content():
    data = load_db_content()
    print('### Pipeline DB ##')
    for k in data.keys():
        print(k, data[k])
    print('##################')


async def add_pipeline(request: web.Request, body) -> web.Response:
    """Creates a pipeline.

    Provides a ready-to-use Jenkins pipeline based on the v2 series of jenkins-pipeline-library.

    :param body:
    :type body: dict | bytes

    """
    pipeline_id = str(uuid.uuid4())
    # body = Pipeline.from_dict(body)

    # FIXME For the time being, we just support one config.yml
    config_yml, composer_yml = JePLUtils.get_sqa_files(
        body['config_data'][0], body['composer_data'])
    print(config_yml)

    # FIXME Get the first defined repo as the main one
    # The main repo should be selected by the user, provided by the client
    # main_repo = body.config_data[0].project_repos[0].repo_id
    # main_repo += ".sqaaas"

    # Create the repository in GitHub
    # with open('.gh_token','r') as f:
    #     token = f.read().strip()
    # gh_utils = GitHubUtils(token)
    # if not gh_utils.get_org_repository(main_repo):
    #     gh_utils.create_org_repository(main_repo)

    # db = load_db_content()
    # db[pipeline_id] = {'sqa_criteria': body.sqa_criteria}
    # store_db_content(db)

    return web.Response(status=200)


async def get_pipelines(request: web.Request) -> web.Response:
    """Gets pipeline IDs.

    Returns the list of IDs for the defined pipelines.

    """
    db = load_db_content()
    return web.json_response(db, status=200)


async def get_pipeline_by_id(request: web.Request, pipeline_id) -> web.Response:
    """Find pipeline by ID



    :param pipeline_id: ID of the pipeline to get
    :type pipeline_id: str

    """
    return web.Response(status=200)


async def get_pipeline_composer(request: web.Request, pipeline_id) -> web.Response:
    """Gets composer configuration used by the pipeline.

    Returns the content of JePL&#39;s docker-compose.yml file. 

    :param pipeline_id: ID of the pipeline to get
    :type pipeline_id: str

    """
    return web.Response(status=200)


async def get_pipeline_config(request: web.Request, pipeline_id) -> web.Response:
    """Gets pipeline&#39;s main configuration.

    Returns the content of JePL&#39;s config.yml file. 

    :param pipeline_id: ID of the pipeline to get
    :type pipeline_id: str

    """
    return web.Response(status=200)


async def get_pipeline_jenkinsfile(request: web.Request, pipeline_id) -> web.Response:
    """Gets Jenkins pipeline definition used by the pipeline.

    Returns the content of JePL&#39;s Jenkinsfile file. 

    :param pipeline_id: ID of the pipeline to get
    :type pipeline_id: str

    """
    return web.Response(status=200)


async def get_pipeline_status(request: web.Request, pipeline_id) -> web.Response:
    """Get pipeline status.

    Obtains the build URL in Jenkins for the given pipeline. 

    :param pipeline_id: ID of the pipeline to get
    :type pipeline_id: str

    """
    return web.Response(status=200)


async def run_pipeline(request: web.Request, pipeline_id) -> web.Response:
    """Runs pipeline.

    Executes the given pipeline by means of the Jenkins API. 

    :param pipeline_id: ID of the pipeline to get
    :type pipeline_id: str

    """
    return web.Response(status=200)
