import json
import logging
import os
import uuid

from typing import List, Dict
from aiohttp import web

from openapi_server.models.pipeline import Pipeline
from openapi_server import util
from openapi_server.controllers.github import GitHubUtils
from openapi_server.controllers.jepl import JePLUtils
from openapi_server.controllers.jenkins import JenkinsUtils


DB_FILE = 'sqaaas.json'
JENKINS_URL = 'https://jenkins.eosc-synergy.eu/'
JENKINS_USER = 'orviz'

logger = logging.getLogger('sqaaas_api.controller')


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
    config_json = body['config_data'][0]
    composer_json = body['composer_data']
    jenkinsfile_data = body['jenkinsfile_data']

    config_yml, composer_yml = JePLUtils.get_sqa_files(
        config_json, composer_json)
    jenkinsfile = JePLUtils.get_jenkinsfile(jenkinsfile_data)

    for repo in list(config_json['config']['project_repos']):
        repo_name = repo + ".sqaaas"
        logger.debug('Using GitHub repository name: %s' % repo_name)

        # Create the repository in GitHub & push JePL files
        with open('.gh_token','r') as f:
            token = f.read().strip()
        logger.debug('Loading GitHub token from local filesystem')
        gh_utils = GitHubUtils(token)

        gh_utils.create_org_repository(repo_name)
        gh_utils.push_file('.sqa/config.yml', config_yml, 'Update config.yml', repo_name)
        logger.debug('Pushing file to GitHub repository <%s>: .sqa/config.yml' % repo_name)
        gh_utils.push_file('.sqa/docker-compose.yml', composer_yml, 'Update docker-compose.yml', repo_name)
        logger.debug('Pushing file to GitHub repository <%s>: .sqa/docker-compose.yml' % repo_name)
        gh_utils.push_file('Jenkinsfile', jenkinsfile, 'Update Jenkinsfile', repo_name)
        logger.debug('Pushing file to GitHub repository <%s>: Jenkinsfile' % repo_name)
        logger.info('GitHub repository <%s> created with the JePL file structure' % repo_name)

    # Trigger GitHub organization re-scan in Jenkins
    with open('.jk_token','r') as f:
        jk_token = f.read().strip()
    logger.debug('Loading Jenkins token from local filesystem')
    jk_utils = JenkinsUtils(JENKINS_URL, JENKINS_USER, jk_token)
    jk_utils.scan_organization()
    # FIXME here we need to wait for scan to finish
    org_jobs = jk_utils.get_job_info('eosc-synergy-org')
    repo_urls = [job['url'] for job in org_jobs['jobs'] if job['name'] == repo_name]
    logger.info('Jenkins job URLs for defined repositories: %s' % repo_urls)

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
