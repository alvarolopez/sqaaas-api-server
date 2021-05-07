import calendar
from datetime import datetime
import io
import itertools
import logging
import urllib
import uuid
from zipfile import ZipFile, ZipInfo

from aiohttp import web
from jinja2 import Environment, PackageLoader
from urllib.parse import urlparse
from deepdiff import DeepDiff

from openapi_server import config
from openapi_server.controllers import db
from openapi_server.controllers.badgr import BadgrUtils
from openapi_server.controllers.github import GitHubUtils
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

TOKEN_BADGR_FILE = config.get_badge(
    'token', fallback='/etc/sqaaas/.badgr_token')
BADGR_URL = config.get_badge('url')
BADGR_USER = config.get_badge('user')
BADGR_ISSUER = config.get_badge('issuer')
BADGR_BADGECLASS = config.get_badge('badgeclass')

logger = logging.getLogger('sqaaas_api.controller')

# Instance of code repo backend object
with open(TOKEN_GH_FILE,'r') as f:
    token = f.read().strip()
logger.debug('Loading GitHub token from local filesystem')
gh_utils = GitHubUtils(token)

# Instance of CI system object
with open(TOKEN_JK_FILE,'r') as f:
    jk_token = f.read().strip()
logger.debug('Loading Jenkins token from local filesystem')
jk_utils = JenkinsUtils(JENKINS_URL, JENKINS_USER, jk_token)

# Instance of Badge issuing service object
with open(TOKEN_BADGR_FILE,'r') as f:
    badgr_token = f.read().strip()
logger.debug('Loading Badgr password from local filesystem')
badgr_utils = BadgrUtils(BADGR_URL, BADGR_USER, badgr_token, BADGR_ISSUER, BADGR_BADGECLASS)


@ctls_utils.debug_request
@ctls_utils.extended_data_validation
async def add_pipeline(request: web.Request, body) -> web.Response:
    """Creates a pipeline.

    Provides a ready-to-use Jenkins pipeline based on the v2 series of jenkins-pipeline-library.

    :param body:
    :type body: dict | bytes

    """
    pipeline_id = str(uuid.uuid4())
    pipeline_name = body['name']
    pipeline_repo = '/'.join([GITHUB_ORG , pipeline_name + '.sqaaas'])
    logger.debug('Repository ID for pipeline name <%s>: %s' % (pipeline_name, pipeline_repo))
    logger.debug('Using GitHub repository name: %s' % pipeline_repo)

    db.add_entry(
        pipeline_id,
        pipeline_repo,
        body
    )

    r = {'id': pipeline_id}
    return web.json_response(r, status=201)


@ctls_utils.debug_request
@ctls_utils.extended_data_validation
@ctls_utils.validate_request
async def update_pipeline_by_id(request: web.Request, pipeline_id, body) -> web.Response:
    """Update pipeline by ID

    :param pipeline_id: ID of the pipeline to get
    :type pipeline_id: str
    :param body:
    :type body: dict | bytes

    """
    pipeline_data = db.get_entry(pipeline_id)
    pipeline_data_raw = pipeline_data['raw_request']
    pipeline_repo = pipeline_data['pipeline_repo']

    config_json, composer_json, jenkinsfile_data = ctls_utils.get_pipeline_data(body)
    config_json_last, composer_json_last, jenkinsfile_data_last = ctls_utils.get_pipeline_data(pipeline_data_raw)

    diff_exists = False
    for elem in [
        (config_json_last, config_json),
        (composer_json_last, composer_json),
        (jenkinsfile_data_last, jenkinsfile_data),
    ]:
        ddiff = DeepDiff(*elem)
        if ddiff:
            diff_exists = True
            logging.debug(ddiff)

    if diff_exists:
        logger.debug('DB-updating modified pipeline on user request: %s' % pipeline_id)
        db.add_entry(
            pipeline_id,
            pipeline_repo,
            body
        )

    return web.Response(status=204)


@ctls_utils.debug_request
@ctls_utils.validate_request
async def delete_pipeline_by_id(request: web.Request, pipeline_id) -> web.Response:
    """Delete pipeline by ID

    :param pipeline_id: ID of the pipeline to get
    :type pipeline_id: str

    """
    pipeline_data = db.get_entry(pipeline_id)
    pipeline_repo = pipeline_data['pipeline_repo']

    if gh_utils.get_repository(pipeline_repo):
        gh_utils.delete_repo(pipeline_repo)
    if 'jenkins' in pipeline_data.keys():
        jk_job_name = pipeline_data['jenkins']['job_name']
        if jk_utils.exist_job(jk_job_name):
            jk_utils.scan_organization()
    else:
        logger.debug('Jenkins job not found. Pipeline might not have been yet executed')

    db.del_entry(pipeline_id)

    return web.Response(status=204)


@ctls_utils.debug_request
async def get_pipelines(request: web.Request) -> web.Response:
    """Gets pipeline IDs.

    Returns the list of IDs for the defined pipelines.

    """
    pipeline_list = []
    for pipeline_id, pipeline_data in db.get_entry().items():
        d = {'id': pipeline_id}
        d.update(pipeline_data['raw_request'])
        pipeline_list.append(d)

    return web.json_response(pipeline_list, status=200)


@ctls_utils.debug_request
@ctls_utils.validate_request
async def get_pipeline_by_id(request: web.Request, pipeline_id) -> web.Response:
    """Find pipeline by ID

    :param pipeline_id: ID of the pipeline to get
    :type pipeline_id: str

    """
    pipeline_data = db.get_entry(pipeline_id)
    pipeline_data_raw = pipeline_data['raw_request']

    r = {'id': pipeline_id}
    r.update(pipeline_data_raw)
    return web.json_response(r, status=200)


@ctls_utils.debug_request
@ctls_utils.validate_request
async def get_pipeline_composer(request: web.Request, pipeline_id) -> web.Response:
    """Gets composer configuration used by the pipeline.

    Returns the content of JePL&#39;s docker-compose.yml file.

    :param pipeline_id: ID of the pipeline to get
    :type pipeline_id: str

    """
    pipeline_data = db.get_entry(pipeline_id)
    pipeline_data_raw = pipeline_data['raw_request']

    r = pipeline_data_raw['composer_data']
    return web.json_response(r, status=200)


@ctls_utils.debug_request
@ctls_utils.validate_request
async def get_pipeline_composer_jepl(request: web.Request, pipeline_id) -> web.Response:
    """Gets JePL composer configuration for the given pipeline.

    Returns the content of JePL&#39;s composer file.

    :param pipeline_id: ID of the pipeline to get
    :type pipeline_id: str

    """
    pipeline_data = db.get_entry(pipeline_id)

    composer_data = pipeline_data['data']['composer']
    r = {
        'file_name': composer_data['file_name'],
        'content': composer_data['data_json']
    }

    return web.json_response(r, status=200)


@ctls_utils.debug_request
@ctls_utils.validate_request
async def get_pipeline_config(request: web.Request, pipeline_id) -> web.Response:
    """Gets pipeline&#39;s main configuration.

    Returns the content of JePL&#39;s config.yml file.

    :param pipeline_id: ID of the pipeline to get
    :type pipeline_id: str

    """
    pipeline_data = db.get_entry(pipeline_id)
    pipeline_data_raw = pipeline_data['raw_request']

    r = pipeline_data_raw['config_data']
    return web.json_response(r, status=200)


@ctls_utils.debug_request
@ctls_utils.validate_request
async def get_pipeline_config_jepl(request: web.Request, pipeline_id) -> web.Response:
    """Gets JePL config configuration for the given pipeline.

    Returns the content of JePL&#39;s config file.

    :param pipeline_id: ID of the pipeline to get
    :type pipeline_id: str

    """
    pipeline_data = db.get_entry(pipeline_id)

    config_data_list = pipeline_data['data']['config']
    r = [{
            'file_name': config_data['file_name'],
            'content': config_data['data_json']
        }
            for config_data in config_data_list
    ]

    return web.json_response(r, status=200)


@ctls_utils.debug_request
@ctls_utils.validate_request
async def get_pipeline_jenkinsfile(request: web.Request, pipeline_id) -> web.Response:
    """Gets Jenkins pipeline definition used by the pipeline.

    Returns the content of JePL&#39;s Jenkinsfile file.

    :param pipeline_id: ID of the pipeline to get
    :type pipeline_id: str

    """
    pipeline_data = db.get_entry(pipeline_id)
    pipeline_data_raw = pipeline_data['raw_request']

    r = pipeline_data_raw['jenkinsfile_data']
    return web.json_response(r, status=200)


@ctls_utils.debug_request
@ctls_utils.validate_request
async def get_pipeline_jenkinsfile_jepl(request: web.Request, pipeline_id) -> web.Response:
    """Gets Jenkins configuration for the given pipeline.

    Returns the content of Jenkinsfile file for the given pipeline.

    :param pipeline_id: ID of the pipeline to get
    :type pipeline_id: str

    """
    pipeline_data = db.get_entry(pipeline_id)
    jenkinsfile = pipeline_data['data']['jenkinsfile']

    r = {
        'file_name': 'Jenkinsfile',
        'content': jenkinsfile
    }

    return web.json_response(r, status=200)


@ctls_utils.debug_request
@ctls_utils.validate_request
async def get_pipeline_status(request: web.Request, pipeline_id) -> web.Response:
    """Get pipeline status.

    Obtains the build URL in Jenkins for the given pipeline.

    :param pipeline_id: ID of the pipeline to get
    :type pipeline_id: str

    """
    pipeline_data = db.get_entry(pipeline_id)

    if 'jenkins' not in pipeline_data.keys():
        _reason = 'Could not retrieve Jenkins job information: Pipeline has not yet ran'
        logger.error(_reason)
        return web.Response(status=422, reason=_reason)

    jenkins_info = pipeline_data['jenkins']
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
            jenkins_info['build_info'].update({
                'url': build_url,
                'number': build_no,
            })
            jenkins_info['scan_org_wait'] = False
        else:
            logger.debug('Job still waiting for scan organization to end')
            build_status = 'WAITING_SCAN_ORG'

    if build_no:
        build_status = jk_utils.get_build_info(
            jk_job_name,
            build_no
        )
    logger.info('Build status <%s> for job: %s (build_no: %s)' % (build_status, jk_job_name, build_no))

    badge_data = None
    if jenkins_info['issue_badge'] and build_status in ['SUCCESS']:
        logger.info('Issuing badge as requested when running the pipeline')
        badge_data = _issue_badge(pipeline_id)
        jenkins_info['issue_badge'] = True

    # Add build status to DB
    db.update_jenkins(
        pipeline_id,
        jk_job_name,
        commit_id=jenkins_info['build_info']['commit_id'],
        commit_url=jenkins_info['build_info']['commit_url'],
        build_no=build_no,
        build_url=build_url,
        scan_org_wait=jenkins_info['scan_org_wait'],
        build_status=build_status,
        issue_badge=jenkins_info['issue_badge'],
        badge_data=badge_data
    )

    r = {
        'build_url': build_url,
        'build_status': build_status
    }
    return web.json_response(r, status=200)


@ctls_utils.debug_request
@ctls_utils.validate_request
async def run_pipeline(request: web.Request, pipeline_id, issue_badge=False) -> web.Response:
    """Runs pipeline.

    Executes the given pipeline by means of the Jenkins API.

    :param pipeline_id: ID of the pipeline to get
    :type pipeline_id: str
    :param issue_badge: Flag to indicate whether a badge shall be issued if the pipeline succeeds
    :type issue_badge: bool

    """
    pipeline_data = db.get_entry(pipeline_id)
    pipeline_repo = pipeline_data['pipeline_repo']

    config_data_list = pipeline_data['data']['config']
    composer_data = pipeline_data['data']['composer']
    jenkinsfile = pipeline_data['data']['jenkinsfile']

    repo_data = gh_utils.get_repository(pipeline_repo)
    if repo_data:
        logger.warning('Repository <%s> already exists!' % repo_data['full_name'])
    else:
        gh_utils.create_org_repository(pipeline_repo)
    commit_id = ctls_utils.push_jepl_files(
        gh_utils,
        pipeline_repo,
        config_data_list,
        composer_data,
        jenkinsfile
    )
    commit_url = gh_utils.get_commit_url(pipeline_repo, commit_id)
    repo_data = gh_utils.get_repository(pipeline_repo)

    _pipeline_repo_name = pipeline_repo.split('/')[-1]
    jk_job_name = '/'.join([
        JENKINS_GITHUB_ORG,
        _pipeline_repo_name,
        repo_data['default_branch']
    ])

    _status = 200
    build_no = None
    build_url = None
    scan_org_wait = False
    if jk_utils.exist_job(jk_job_name):
        logger.warning('Jenkins job <%s> already exists!' % jk_job_name)
        last_build_data = jk_utils.build_job(jk_job_name)
        build_no = last_build_data['number']
        build_url = last_build_data['url']
        logger.info('Jenkins job build URL obtained for repository <%s>: %s' % (pipeline_repo, build_url))
    else:
        jk_utils.scan_organization()
        scan_org_wait = True
        _status = 204

    if issue_badge:
        logger.debug('Badge issuing (<issue_badge> flag) is requested for the current build: %s' % commit_id)

    db.update_jenkins(
        pipeline_id,
        jk_job_name,
        commit_id,
        commit_url,
        build_no=build_no,
        build_url=build_url,
        scan_org_wait=scan_org_wait,
        issue_badge=issue_badge
    )

    r = {'build_url': build_url}
    return web.json_response(r, status=_status)


@ctls_utils.debug_request
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
    pipeline_data = db.get_entry(pipeline_id)
    config_data_list = pipeline_data['data']['config']
    composer_data = pipeline_data['data']['composer']
    jenkinsfile = pipeline_data['data']['jenkinsfile']
    ctls_utils.push_jepl_files(
        gh_utils,
        fork_repo,
        config_data_list,
        composer_data,
        jenkinsfile,
        branch=fork_default_branch)
    # step 3: create PR
    pr = gh_utils.create_pull_request(
        upstream_repo,
        fork_repo,
        branch=fork_default_branch)
    pr_url = pr['html_url']

    r = {'pull_request_url': pr_url}
    return web.json_response(r, status=200)


@ctls_utils.debug_request
@ctls_utils.validate_request
async def get_compressed_files(request: web.Request, pipeline_id) -> web.Response:
    """Get JePL files in compressed format.

    Obtains the generated JePL files in compressed format.

    :param pipeline_id: ID of the pipeline to get
    :type pipeline_id: str

    """
    pipeline_data = db.get_entry(pipeline_id)

    config_data_list = pipeline_data['data']['config']
    composer_data = pipeline_data['data']['composer']
    jenkinsfile = pipeline_data['data']['jenkinsfile']

    config_yml_list = [
        (data['file_name'], data['data_yml'])
            for data in config_data_list
    ]
    composer_yml = [(
        composer_data['file_name'],
        composer_data['data_yml']
    )]
    jenkinsfile = [(
        'Jenkinsfile', jenkinsfile
    )]

    binary_stream = io.BytesIO()
    with ZipFile(binary_stream, 'w') as zfile:
        for t in config_yml_list + composer_yml + jenkinsfile:
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


async def _issue_badge(pipeline_id):
    pipeline_data = db.get_entry(pipeline_id)
    pipeline_repo = pipeline_data['pipeline_repo']

    # Get 'ci_build_url' & 'commit_url'
    try:
        jenkins_info = pipeline_data['jenkins']
        build_info = jenkins_info['build_info']
        build_status = build_info['status']
        if not build_status in ['SUCCESS', 'UNSTABLE']:
            _reason = 'Cannot issue a badge for pipeline <%s>: build status is \'%s\'' % (pipeline_id, build_status)
            logger.error(_reason)
            return web.Response(status=422, reason=_reason)
    except KeyError:
        _reason = 'Could not retrieve Jenkins job information: Pipeline has not ran yet'
        logger.error(_reason)
        return web.Response(status=422, reason=_reason)
    build_url = build_info['url']
    logger.debug('Getting build URL from Jenkins associated data: %s' % build_url)
    commit_id = build_info['commit_id']
    commit_url = build_info['commit_url']
    logger.debug('Getting commit URL from Jenkins associated data: %s' % commit_url)

    # Get 'sw_criteria' & 'srv_criteria'
    SW_CODE_PREFIX = 'qc_'
    SRV_CODE_PREFIX = 'SvcQC'
    logger.debug('Filtering Software criteria codes by <%s> prefix' % SW_CODE_PREFIX)
    logger.debug('Filtering Service criteria codes by <%s> prefix' % SRV_CODE_PREFIX)
    config_data_list = pipeline_data['data']['config']
    criteria = [
        config_data['data_json']['sqa_criteria'].keys()
            for config_data in config_data_list
    ]
    criteria = list(itertools.chain.from_iterable(criteria))
    sw_criteria = [
        criterion
            for criterion in criteria
                if criterion.startswith(SW_CODE_PREFIX)
    ]
    srv_criteria = [
        criterion
            for criterion in criteria
                if criterion.startswith(SRV_CODE_PREFIX)
    ]
    logger.debug('Obtained Software criteria: %s' % sw_criteria)
    logger.debug('Obtained Service criteria: %s' % srv_criteria)

    logger.info('Issuing badge for pipeline <%s>' % pipeline_id)
    try:
        badge_data = badgr_utils.issue_badge(
            commit_id=commit_id,
            commit_url=commit_url,
            ci_build_url=build_url,
            sw_criteria=sw_criteria,
            srv_criteria=srv_criteria
        )
    except Exception as e:
        _reason = 'Cannot issue a badge for pipeline <%s>: %s' % (pipeline_id, e)
        logger.error(_reason)
        return web.Response(status=502, reason=_reason)
    else:
        logger.info('Badge successfully issued: %s' % badge_data['openBadgeId'])
        return badge_data


@ctls_utils.debug_request
@ctls_utils.validate_request
async def issue_badge(request: web.Request, pipeline_id) -> web.Response:
    """Issues a quality badge.

    Uses Badgr API to issue a badge after successful pipeline execution.

    :param pipeline_id: ID of the pipeline to get
    :type pipeline_id: str

    """
    pipeline_data = db.get_entry(pipeline_id)
    try:
        jenkins_info = pipeline_data['jenkins']
    except KeyError:
        _reason = 'Could not retrieve Jenkins job information: Pipeline has not ran yet'
        logger.error(_reason)
        return web.Response(status=422, reason=_reason)

    badge_data = _issue_badge(pipeline_id)

    # Add badge data to DB
    db.update_jenkins(
        pipeline_id,
        jenkins_info['job_name'],
        commit_id=jenkins_info['build_info']['commit_id'],
        commit_url=jenkins_info['build_info']['commit_url'],
        build_no=jenkins_info['build_info']['number'],
        build_url=jenkins_info['build_info']['url'],
        scan_org_wait=jenkins_info['scan_org_wait'],
        build_status=jenkins_info['build_info']['status'],
        issue_badge=False,
        badge_data=jenkins_info['build_info']['badge']
    )
    return web.json_response(badge_data, status=200)


@ctls_utils.debug_request
@ctls_utils.validate_request
async def get_badge(request: web.Request, pipeline_id, share=None) -> web.Response:
    """Gets badge data associated with the given pipeline

    Returns the badge data associated with the pipeline.

    :param pipeline_id: ID of the pipeline to get
    :type pipeline_id: str
    :param share: Returns the badge in the specific format
    :type share: str

    """
    pipeline_data = db.get_entry(pipeline_id)

    try:
        build_info = pipeline_data['jenkins']['build_info']
        commit_url = build_info['commit_url']
        badge_data = build_info['badge']
        if not badge_data:
            raise KeyError
    except KeyError:
        _reason = 'Badge not issued for pipeline <%s>' % pipeline_id
        logger.error(_reason)
        return web.Response(status=422, reason=_reason)

    logger.info('Badge <%s> found' % badge_data['openBadgeId'])

    if share == 'html':
        env = Environment(
            loader=PackageLoader('openapi_server', 'templates')
        )
        template = env.get_template('embed_badge.html')

        dt = datetime.strptime(
            badge_data['createdAt'],
            '%Y-%m-%dT%H:%M:%S.%fZ'
        )
        html_rendered = template.render({
            'openBadgeId': badge_data['openBadgeId'],
            'commit_url': commit_url,
            'image': badge_data['image'],
            'badgr_badgeclass': BADGR_BADGECLASS,
            'award_month': calendar.month_name[dt.month],
            'award_day': dt.day,
            'award_year': dt.year,
        })

        return web.Response(
            text=html_rendered,
            content_type='text/html',
            status=200
        )

    return web.json_response(badge_data, status=200)
