import functools
import io
import json
import logging
import os
import uuid
import time
from zipfile import ZipFile, ZipInfo

from typing import List, Dict
from aiohttp import web
from urllib.parse import urlparse

from openapi_server.models.pipeline import Pipeline
from openapi_server import util
from openapi_server.controllers.github import GitHubUtils
from openapi_server.controllers.jepl import JePLUtils
from openapi_server.controllers.jenkins import JenkinsUtils
from openapi_server.controllers import utils as ctls_utils
from openapi_server.models.inline_object import InlineObject


DB_FILE = '/sqaaas/sqaaas.json'
GITHUB_ORG = 'EOSC-Synergy'
JENKINS_URL = 'https://jenkins.eosc-synergy.eu/'
JENKINS_USER = 'orviz'
JENKINS_GITHUB_ORG = 'eosc-synergy-org'
JENKINS_SCAN_TIMEOUT_SECONDS = 150
JENKINS_SCAN_CHECK_SECONDS = 30

logger = logging.getLogger('sqaaas_api.controller')


with open('/sqaaas/.gh_token','r') as f:
    token = f.read().strip()
logger.debug('Loading GitHub token from local filesystem')
gh_utils = GitHubUtils(token)

with open('/sqaaas/.jk_token','r') as f:
    jk_token = f.read().strip()
logger.debug('Loading Jenkins token from local filesystem')
jk_utils = JenkinsUtils(JENKINS_URL, JENKINS_USER, jk_token)


def validate_request(f):
  @functools.wraps(f)
  def decorated_function(*args, **kwargs):
    _pipeline_id = kwargs['pipeline_id']
    try:
        uuid.UUID(_pipeline_id, version=4)
        db = load_db_content()
        if _pipeline_id in list(db):
            logger.debug('Pipeline <%s> found in DB' % _pipeline_id)
        else:
            logger.warning('Pipeline not found!: %s' % _pipeline_id)
            return web.Response(status=404)
    except ValueError:
        logger.warning('Invalid pipeline ID supplied!: %s' % _pipeline_id)
        return web.Response(status=400)
    return f(*args, **kwargs)
  return decorated_function


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
    db = load_db_content()
    logger.debug('Current DB content: %s' % list(db))


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

    # FIXME sqaaas_repo must be provided by the user
    pipeline_name = body['name']
    pipeline_repo = '/'.join([GITHUB_ORG , pipeline_name + '.sqaaas'])
    logger.debug('Repository ID for pipeline name <%s>: %s' % (pipeline_name, pipeline_repo))
    logger.debug('Using GitHub repository name: %s' % pipeline_repo)

    db = load_db_content()
    db[pipeline_id] = {
        'pipeline_repo': pipeline_repo,
        'data': {
            'config_data': config_json,
            'composer_data': composer_json,
            'jenkinsfile': jenkinsfile_data
        }
    }
    store_db_content(db)

    r = {'id': pipeline_id}
    return web.json_response(r, status=200)


@validate_request
async def delete_pipeline_by_id(request: web.Request, pipeline_id) -> web.Response:
    """Delete pipeline by ID

    :param pipeline_id: ID of the pipeline to get
    :type pipeline_id: str

    """
    db = load_db_content()
    db.pop(pipeline_id)
    logger.info('Pipeline <%s> removed from DB' % pipeline_id)

    return web.Response(status=200)


async def get_pipelines(request: web.Request) -> web.Response:
    """Gets pipeline IDs.

    Returns the list of IDs for the defined pipelines.

    """
    db = load_db_content()
    return web.json_response(db, status=200)


@validate_request
async def get_pipeline_by_id(request: web.Request, pipeline_id) -> web.Response:
    """Find pipeline by ID

    :param pipeline_id: ID of the pipeline to get
    :type pipeline_id: str

    """
    db = load_db_content()
    r = db[pipeline_id]
    return web.json_response(r, status=200)


async def get_pipeline_composer(request: web.Request, pipeline_id) -> web.Response:
    """Gets composer configuration used by the pipeline.

    Returns the content of JePL&#39;s docker-compose.yml file. 

    :param pipeline_id: ID of the pipeline to get
    :type pipeline_id: str

    """
    db = load_db_content()
    pipeline_data = db[pipeline_id]['data']
    r = pipeline_data['composer_data']
    return web.json_response(r, status=200)


async def get_pipeline_config(request: web.Request, pipeline_id) -> web.Response:
    """Gets pipeline&#39;s main configuration.

    Returns the content of JePL&#39;s config.yml file.

    :param pipeline_id: ID of the pipeline to get
    :type pipeline_id: str

    """
    db = load_db_content()
    pipeline_data = db[pipeline_id]['data']
    r = pipeline_data['config_data']
    return web.json_response(r, status=200)


async def get_pipeline_jenkinsfile(request: web.Request, pipeline_id) -> web.Response:
    """Gets Jenkins pipeline definition used by the pipeline.

    Returns the content of JePL&#39;s Jenkinsfile file.

    :param pipeline_id: ID of the pipeline to get
    :type pipeline_id: str

    """
    db = load_db_content()
    pipeline_data = db[pipeline_id]['data']
    r = pipeline_data['jenkinsfile']
    return web.json_response(r, status=200)


async def get_pipeline_status(request: web.Request, pipeline_id) -> web.Response:
    """Get pipeline status.

    Obtains the build URL in Jenkins for the given pipeline.

    :param pipeline_id: ID of the pipeline to get
    :type pipeline_id: str

    """
    db = load_db_content()
    build_url = db[pipeline_id]['build']['url']
    logger.debug('Loading pipeline <%s> from DB' % pipeline_id)

    jk_job_name = db[pipeline_id]['jk_job_name']
    build_no = db[pipeline_id]['build']['number']
    build_status = jk_utils.get_build_status(
        jk_job_name,
        build_no
    )
    logger.info('Build status <%s> for job: %s (build_no: %s)' % (build_status, jk_job_name, build_no))

    r = {'build_status': build_status}
    return web.json_response(r, status=200)


@validate_request
async def run_pipeline(request: web.Request, pipeline_id) -> web.Response:
    """Runs pipeline.

    Executes the given pipeline by means of the Jenkins API.

    :param pipeline_id: ID of the pipeline to get
    :type pipeline_id: str

    """
    db = load_db_content()
    pipeline_repo = db[pipeline_id]['pipeline_repo']
    pipeline_data = db[pipeline_id]['data']
    logger.debug('Loading pipeline <%s> from DB' % pipeline_id)

    repo_data = gh_utils.get_repository(pipeline_repo)
    if repo_data:
        logger.warning('Repository <%s> already exists!' % repo_data['full_name'])
    else:
        gh_utils.create_org_repository(pipeline_repo)
    ctls_utils.push_jepl_files(
        gh_utils,
        pipeline_repo,
        pipeline_data['config_data'],
        pipeline_data['composer_data'],
        pipeline_data['jenkinsfile'])
    repo_data = gh_utils.get_repository(pipeline_repo)

    _pipeline_repo_name = pipeline_repo.split('/')[-1]
    jk_job_name = '/'.join([
        JENKINS_GITHUB_ORG,
        _pipeline_repo_name,
        repo_data['default_branch']
    ])
    db[pipeline_id]['jk_job_name'] = jk_job_name

    last_build_data = None
    if jk_utils.get_job_url(_pipeline_repo_name):
        logger.warning('Jenkins job <%s> already exists!' % jk_job_name)
        last_build_data = jk_utils.build_job(jk_job_name)
    else:
        jk_utils.scan_organization()
        _loop_counter = 1
        _loop_total = int(JENKINS_SCAN_TIMEOUT_SECONDS/JENKINS_SCAN_CHECK_SECONDS)
        _build_data = {}
        while not _build_data or _loop_counter < _loop_total:
            time.sleep(30)
            _build_data = jk_utils.get_job_info(jk_job_name)
            logger.debug('Waiting for scan organization process to finish (loop %s out of %s)..' % (_loop_counter, _loop_total))
            _loop_counter += 1
        logger.debug('Scan organization finished')
        last_build_data = _build_data['lastBuild']
    build_no = last_build_data['number']
    build_url = last_build_data['url']
    logger.info('Jenkins job build URL obtained for repository <%s>: %s' % (pipeline_repo, build_url))

    db[pipeline_id]['build'] = {
        'number': build_no,
        'url': build_url
    }
    store_db_content(db)

    r = {'build_url': build_url}
    return web.json_response(r, status=200)


@validate_request
async def create_pull_request(request: web.Request, pipeline_id, body) -> web.Response:
    """Creates pull request with JePL files.

    Create a pull request with the generated JePL files.

    :param pipeline_id: ID of the pipeline to get
    :type pipeline_id: str
    :param body:
    :type body: dict | bytes

    """
    body = InlineObject.from_dict(body)
    upstream_repo = urlparse(body.repo).path
    upstream_repo = upstream_repo.lstrip('/')
    logger.debug('Upstream repository path: %s' % upstream_repo)

    # step 1: create the fork
    fork = gh_utils.create_fork(upstream_repo)
    fork_repo = fork['full_name'].lower()
    fork_default_branch = fork['default_branch']
    # step 2: push JePL files to fork
    db = load_db_content()
    pipeline_data = db[pipeline_id]['data']
    ctls_utils.push_jepl_files(
        gh_utils,
        fork_repo,
        pipeline_data['config_data'],
        pipeline_data['composer_data'],
        pipeline_data['jenkinsfile'])
    # step 3: create PR
    pr = gh_utils.create_pull_request(
        upstream_repo,
        fork_repo,
        branch=fork_default_branch)
    pr_url = pr['url']

    r = {'pull_request_url': pr_url}
    return web.json_response(r, status=200)


@validate_request
async def get_compressed_files(request: web.Request, pipeline_id) -> web.Response:
    """Get JePL files in compressed format.

    Obtains the generated JePL files in compressed format.

    :param pipeline_id: ID of the pipeline to get
    :type pipeline_id: str

    """
    db = load_db_content()
    pipeline_data = db[pipeline_id]['data']

    config_yml, composer_yml, jenkinsfile = ctls_utils.get_jepl_files(
        pipeline_data['config_data'],
        pipeline_data['composer_data'],
        pipeline_data['jenkinsfile']
    )

    binary_stream = io.BytesIO()
    with ZipFile(binary_stream, 'w') as zfile:
        for t in [('.sqa/config.yml', config_yml),
                  ('.sqa/docker-compose.yml', composer_yml),
                  ('Jenkinsfile', jenkinsfile)]:
            zinfo = ZipInfo(t[0])
            zfile.writestr(zinfo, t[1].encode('UTF-8'))

    return web.Response(
        body=binary_stream.getbuffer(),
        headers={'Content-Encoding':'gzip'},
        status=200)
