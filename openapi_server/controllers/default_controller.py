import io
import logging
import time
import uuid
from zipfile import ZipFile, ZipInfo

from typing import List, Dict
from aiohttp import web
from urllib.parse import urlparse
from deepdiff import DeepDiff

from openapi_server import config
from openapi_server.models.pipeline import Pipeline
from openapi_server import util
from openapi_server.controllers import db
from openapi_server.controllers.github import GitHubUtils
from openapi_server.controllers.jepl import JePLUtils
from openapi_server.controllers.jenkins import JenkinsUtils
from openapi_server.controllers import utils as ctls_utils
from openapi_server.models.inline_object import InlineObject


TOKEN_GH_FILE = config.get_repo(
    'token', fallback='/etc/sqaaas/.gh_token')
GITHUB_ORG = config.get_repo('organization')

TOKEN_JK_FILE = config.get_ci(
    'token', fallback='/etc/sqaaas/.jk_token')
JENKINS_URL = config.get_ci('url')
JENKINS_USER = config.get_ci('user')
JENKINS_GITHUB_ORG = config.get_ci('github_organization_name')

logger = logging.getLogger('sqaaas_api.controller')

with open(TOKEN_GH_FILE,'r') as f:
    token = f.read().strip()
logger.debug('Loading GitHub token from local filesystem')
gh_utils = GitHubUtils(token)

with open(TOKEN_JK_FILE,'r') as f:
    jk_token = f.read().strip()
logger.debug('Loading Jenkins token from local filesystem')
jk_utils = JenkinsUtils(JENKINS_URL, JENKINS_USER, jk_token)


async def add_pipeline(request: web.Request, body) -> web.Response:
    """Creates a pipeline.

    Provides a ready-to-use Jenkins pipeline based on the v2 series of jenkins-pipeline-library.

    :param body:
    :type body: dict | bytes

    """
    pipeline_id = str(uuid.uuid4())
    # body = Pipeline.from_dict(body)

    config_json, composer_json, jenkinsfile_data = ctls_utils.get_pipeline_data(body)

    # FIXME sqaaas_repo must be provided by the user
    pipeline_name = body['name']
    pipeline_repo = '/'.join([GITHUB_ORG , pipeline_name + '.sqaaas'])
    logger.debug('Repository ID for pipeline name <%s>: %s' % (pipeline_name, pipeline_repo))
    logger.debug('Using GitHub repository name: %s' % pipeline_repo)

    _db = db.load_content()
    _db[pipeline_id] = {
        'pipeline_repo': pipeline_repo,
        'data': {
            'config_data': config_json,
            'composer_data': composer_json,
            'jenkinsfile': jenkinsfile_data
        }
    }
    db.store_content(_db)

    r = {'id': pipeline_id}
    return web.json_response(r, status=201)


@ctls_utils.validate_request
async def update_pipeline_by_id(request: web.Request, pipeline_id, body) -> web.Response:
    """Update pipeline by ID

    :param pipeline_id: ID of the pipeline to get
    :type pipeline_id: str
    :param body:
    :type body: dict | bytes

    """
    _db = db.load_content()
    pipeline_repo = _db[pipeline_id]['pipeline_repo']
    pipeline_data = _db[pipeline_id]['data']
    logger.debug('Loading pipeline <%s> from DB' % pipeline_id)

    config_json, composer_json, jenkinsfile_data = ctls_utils.get_pipeline_data(body)

    diff_exists = False
    for elem in [
        (pipeline_data['config_data'], config_json),
        (pipeline_data['composer_data'], composer_json),
        (pipeline_data['jenkinsfile'], jenkinsfile_data),
    ]:
        ddiff = DeepDiff(*elem)
        if ddiff:
            diff_exists = True
            logging.debug(ddiff)

    if diff_exists:
        logging.debug('DB-updating modified pipeline on user request: %s' % pipeline_id)
        _db[pipeline_id] = {
            'pipeline_repo': pipeline_repo,
            'data': {
                'config_data': config_json,
                'composer_data': composer_json,
                'jenkinsfile': jenkinsfile_data
            }
        }
        db.store_content(_db)

    return web.Response(status=204)


@ctls_utils.validate_request
async def delete_pipeline_by_id(request: web.Request, pipeline_id) -> web.Response:
    """Delete pipeline by ID

    :param pipeline_id: ID of the pipeline to get
    :type pipeline_id: str

    """
    _db = db.load_content()
    pipeline_repo = _db[pipeline_id]['pipeline_repo']
    if gh_utils.get_repository(pipeline_repo):
        gh_utils.delete_repo(pipeline_repo)
    if 'jenkins' in _db[pipeline_id].keys():
        jk_job_name = _db[pipeline_id]['jenkins']['job_name']
        if jk_utils.exist_job(jk_job_name):
            jk_utils.scan_organization()
    else:
        logger.debug('Jenkins job not found. Pipeline might not have been yet executed')
    _db.pop(pipeline_id)
    logger.info('Pipeline <%s> removed from DB' % pipeline_id)

    return web.Response(status=204)


async def get_pipelines(request: web.Request) -> web.Response:
    """Gets pipeline IDs.

    Returns the list of IDs for the defined pipelines.

    """
    _db = db.load_content()
    return web.json_response(_db, status=200)


@ctls_utils.validate_request
async def get_pipeline_by_id(request: web.Request, pipeline_id) -> web.Response:
    """Find pipeline by ID

    :param pipeline_id: ID of the pipeline to get
    :type pipeline_id: str

    """
    _db = db.load_content()
    r = _db[pipeline_id]
    return web.json_response(r, status=200)


@ctls_utils.validate_request
async def get_pipeline_composer(request: web.Request, pipeline_id) -> web.Response:
    """Gets composer configuration used by the pipeline.

    Returns the content of JePL&#39;s docker-compose.yml file.

    :param pipeline_id: ID of the pipeline to get
    :type pipeline_id: str

    """
    _db = db.load_content()
    pipeline_data = _db[pipeline_id]['data']
    r = pipeline_data['composer_data']
    return web.json_response(r, status=200)


@ctls_utils.validate_request
async def get_pipeline_config(request: web.Request, pipeline_id) -> web.Response:
    """Gets pipeline&#39;s main configuration.

    Returns the content of JePL&#39;s config.yml file.

    :param pipeline_id: ID of the pipeline to get
    :type pipeline_id: str

    """
    _db = db.load_content()
    pipeline_data = _db[pipeline_id]['data']
    r = pipeline_data['config_data']
    return web.json_response(r, status=200)


@ctls_utils.validate_request
async def get_pipeline_jenkinsfile(request: web.Request, pipeline_id) -> web.Response:
    """Gets Jenkins pipeline definition used by the pipeline.

    Returns the content of JePL&#39;s Jenkinsfile file.

    :param pipeline_id: ID of the pipeline to get
    :type pipeline_id: str

    """
    _db = db.load_content()
    pipeline_data = _db[pipeline_id]['data']
    r = pipeline_data['jenkinsfile']
    return web.json_response(r, status=200)


@ctls_utils.validate_request
async def get_pipeline_status(request: web.Request, pipeline_id) -> web.Response:
    """Get pipeline status.

    Obtains the build URL in Jenkins for the given pipeline.

    :param pipeline_id: ID of the pipeline to get
    :type pipeline_id: str

    """
    logger.debug('Loading pipeline <%s> from DB' % pipeline_id)
    _db = db.load_content()

    if 'jenkins' not in _db[pipeline_id].keys():
        logger.error('Could not retrieve Jenkins job information: Pipeline has not yet ran')
        return web.Response(status=422)

    jenkins_info = _db[pipeline_id]['jenkins']
    jk_job_name = jenkins_info['job_name']
    build_url = jenkins_info['build_info']['url']
    build_no = jenkins_info['build_info']['number']

    if jenkins_info['scan_org_wait']:
        logger.debug('scan_org_wait still enabled for pipeline job: %s' % jk_job_name)
        last_build_data = jk_utils.get_job_info(jk_job_name)
        if last_build_data:
            build_url = last_build_data['lastBuild']['url']
            build_no = last_build_data['lastBuild']['number']
            logger.info('Jenkins job build URL (after Scan Organization finished) obtained: %s' % build_url)
            jenkins_info['build_info'] = {
                'url': build_url,
                'number': build_no,
            }
            jenkins_info['scan_org_wait'] = False
        else:
            logger.debug('Job still waiting for scan organization to end')
            build_status = 'WAITING_SCAN_ORG'

    if build_no:
        build_status = jk_utils.get_build_status(
            jk_job_name,
            build_no
        )
    logger.info('Build status <%s> for job: %s (build_no: %s)' % (build_status, jk_job_name, build_no))

    r = {
        'build_url': build_url,
        'build_status': build_status
    }
    return web.json_response(r, status=200)


@ctls_utils.validate_request
async def run_pipeline(request: web.Request, pipeline_id) -> web.Response:
    """Runs pipeline.

    Executes the given pipeline by means of the Jenkins API.

    :param pipeline_id: ID of the pipeline to get
    :type pipeline_id: str

    """
    _db = db.load_content()
    pipeline_repo = _db[pipeline_id]['pipeline_repo']
    pipeline_data = _db[pipeline_id]['data']
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
        pipeline_data['composer_data'])
    repo_data = gh_utils.get_repository(pipeline_repo)

    _pipeline_repo_name = pipeline_repo.split('/')[-1]
    jk_job_name = '/'.join([
        JENKINS_GITHUB_ORG,
        _pipeline_repo_name,
        repo_data['default_branch']
    ])
    _db[pipeline_id]['jenkins'] = {
        'job_name': jk_job_name,
        'build_info': {
            'number': None,
            'url': None,
        },
        'scan_org_wait': False
    }

    _status = 200
    if jk_utils.exist_job(jk_job_name):
        logger.warning('Jenkins job <%s> already exists!' % jk_job_name)
        last_build_data = jk_utils.build_job(jk_job_name)
        build_no = last_build_data['number']
        build_url = last_build_data['url']
        logger.info('Jenkins job build URL obtained for repository <%s>: %s' % (pipeline_repo, build_url))
        _db[pipeline_id]['jenkins']['build_info'] = {
            'number': build_no,
            'url': build_url
        }
    else:
        jk_utils.scan_organization()
        _db[pipeline_id]['jenkins']['scan_org_wait'] = True
        _status = 204

    db.store_content(_db)

    r = {'build_url': _db[pipeline_id]['jenkins']['build_info']['url']}
    return web.json_response(r, status=_status)


@ctls_utils.validate_request
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
    fork_repo, fork_default_branch = gh_utils.create_fork(upstream_repo)
    logger.debug('Using fork default branch: %s' % fork_default_branch)
    # step 2: push JePL files to fork
    _db = db.load_content()
    pipeline_data = _db[pipeline_id]['data']
    ctls_utils.push_jepl_files(
        gh_utils,
        fork_repo,
        pipeline_data['config_data'],
        pipeline_data['composer_data'],
        branch=fork_default_branch)
    # step 3: create PR
    pr = gh_utils.create_pull_request(
        upstream_repo,
        fork_repo,
        branch=fork_default_branch)
    pr_url = pr['html_url']

    r = {'pull_request_url': pr_url}
    return web.json_response(r, status=200)


@ctls_utils.validate_request
async def get_compressed_files(request: web.Request, pipeline_id) -> web.Response:
    """Get JePL files in compressed format.

    Obtains the generated JePL files in compressed format.

    :param pipeline_id: ID of the pipeline to get
    :type pipeline_id: str

    """
    _db = db.load_content()
    pipeline_data = _db[pipeline_id]['data']

    config_yml, composer_yml, jenkinsfile = ctls_utils.get_jepl_files(
        pipeline_data['config_data'],
        pipeline_data['composer_data']
    )

    binary_stream = io.BytesIO()
    with ZipFile(binary_stream, 'w') as zfile:
        for t in [('.sqa/config.yml', config_yml),
                  ('.sqa/docker-compose.yml', composer_yml),
                  ('Jenkinsfile', jenkinsfile)]:
            zinfo = ZipInfo(t[0])
            zfile.writestr(zinfo, t[1].encode('UTF-8'))

    zip_data = binary_stream.getbuffer()
    response = web.StreamResponse()
    response.content_type = 'application/zip'
    response.content_length = len(zip_data)
    response.headers.add(
        'Content-Disposition', 'attachment; filename="sqaaas.zip"')
    await response.prepare(request)
    await response.write(zip_data)

    return response
