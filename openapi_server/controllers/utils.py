import functools
import logging
import namegenerator
import re
import uuid

from aiohttp import web

from openapi_server.controllers import db
from openapi_server.controllers.jepl import JePLUtils

from github.GithubException import GithubException
from github.GithubException import UnknownObjectException
from jenkins import JenkinsException


logger = logging.getLogger('sqaaas_api.controller')


def upstream_502_response(r):
    return web.json_response(
        r,
        status=502,
        reason='Unsuccessful request to upstream service API')


def validate_request(f):
    @functools.wraps(f)
    async def decorated_function(*args, **kwargs):
        _pipeline_id = kwargs['pipeline_id']
        try:
            uuid.UUID(_pipeline_id, version=4)
            _db = db.load_content()
            if _pipeline_id in list(_db):
                logger.debug('Pipeline <%s> found in DB' % _pipeline_id)
            else:
                _reason = 'Pipeline not found!: %s' % _pipeline_id
                logger.warning(_reason)
                return web.Response(status=404, reason=_reason)
        except ValueError:
            _reason = 'Invalid pipeline ID supplied!: %s' % _pipeline_id
            logger.warning(_reason)
            return web.Response(status=400, reason=_reason)
        try:
            logger.debug('Running decorated method <%s>' % f.__name__)
            ret = await f(*args, **kwargs)
        except UnknownObjectException as e:
            _status = e.status
            _reason = e.data['message']
            logger.error('(GitHub) %s (exit code: %s)' % (_reason, _status))
            r = {'upstream_status': _status, 'upstream_reason': _reason}
            return upstream_502_response(r)
        except GithubException as e:
            _status = e.status
            _reason = e.data['errors'][0]['message']
            logger.error('(GitHub) %s (exit code: %s)' % (_reason, _status))
            r = {'upstream_status': _status, 'upstream_reason': _reason}
            return upstream_502_response(r)
        except JenkinsException as e:
            msg_first_line = str(e).splitlines()[0]
            logger.error('(Jenkins) %s' % msg_first_line)
            _reason = msg_first_line
            _status = 404
            _status_regexp = re.search('.+\[(40\d{1})\].+', _reason)
            if _status_regexp:
                _status = int(_status_regexp.groups()[0])
            r = {'upstream_status': _status, 'upstream_reason': _reason}
            return upstream_502_response(r)
        return ret
    return decorated_function


def get_pipeline_data(request_body):
    """Get pipeline data.

    Obtains the pipeline data from the API request.
    """
    # NOTE For the time being, we just support one config.yml
    config_json = request_body['config_data'][0]
    composer_json = request_body['composer_data']
    jenkinsfile_data = request_body['jenkinsfile_data']

    return (config_json, composer_json, jenkinsfile_data)


def process_extra_data(config_json, composer_json):
    # Docker Compose specific
    for srv_name, srv_data in composer_json['services'].items():
        ## Set JPL_DOCKER* envvars
        if 'registry' in srv_data['image'].keys():
            registry_data = srv_data['image'].pop('registry')
            if not 'environment' in config_json.keys():
                config_json['environment'] = {}
            # JPL_DOCKERPUSH
            if registry_data['push']:
                srv_push = config_json['environment'].get('JPL_DOCKERPUSH', '')
                srv_push += ' %s' % srv_name
                srv_push = srv_push.strip()
                config_json['environment']['JPL_DOCKERPUSH'] = srv_push
            # JPL_DOCKERSERVER: current JePL 2.1.0 does not support 1-to-1 in image-to-registry
            # so defaulting to the last match
            if registry_data['url']:
                config_json['environment']['JPL_DOCKERSERVER'] = registry_data['url']
        ## Set 'image' property as string (required by Docker Compose)
        srv_data['image'] = srv_data['image']['name']
        ## Set 'working_dir' to the same path as the first volume target
        ## NOTE Setting working_dir only makes sense when only one volume is expected!
        srv_data['working_dir'] = srv_data['volumes'][0]['target']
    # Multiple stages (split config.yml, Jenkins when clause)
    config_json_list = []
    stage_data_list = []
    for criterion_name, criterion_data in config_json['sqa_criteria'].items():
        if 'when' in criterion_data.keys():
            config_json_copy = config_json.copy()
            config_json_copy['sqa_criteria'] = {criterion_name: criterion_data}
            random_fname = '.'.join([
            	'config',
                namegenerator.gen(),
                'json'
            ])
            config_json_list.append((random_fname, config_json_copy))

            when_data = criterion_data.pop('when')
            stage_data_list.append((random_fname, when_data))

    return (config_json, composer_json)


def get_jepl_files(config_json, composer_json, jenkinsfile):
    # Extract & process those data that are not directly translated into
    # the composer and JePL config
    config_json, composer_json = process_extra_data(
        config_json,
        composer_json)

    config_yml, composer_yml = JePLUtils.get_sqa_files(
        config_json,
        composer_json)
    jenkinsfile = JePLUtils.get_jenkinsfile(jenkinsfile)

    return (config_yml, composer_yml, jenkinsfile)


def push_jepl_files(gh_utils, repo, config_json, composer_json, jenkinsfile, branch='sqaaas'):
    config_yml, composer_yml, jenkinsfile = get_jepl_files(
        config_json,
        composer_json,
        jenkinsfile)
    logger.debug('Pushing file to GitHub repository <%s>: .sqa/config.yml' % repo)
    gh_utils.push_file('.sqa/config.yml', config_yml, 'Update config.yml', repo, branch=branch)
    logger.debug('Pushing file to GitHub repository <%s>: .sqa/docker-compose.yml' % repo)
    gh_utils.push_file('.sqa/docker-compose.yml', composer_yml, 'Update docker-compose.yml', repo, branch=branch)
    logger.debug('Pushing file to GitHub repository <%s>: Jenkinsfile' % repo)
    gh_utils.push_file('Jenkinsfile', jenkinsfile, 'Update Jenkinsfile', repo, branch=branch)
    logger.info('GitHub repository <%s> created with the JePL file structure' % repo)
