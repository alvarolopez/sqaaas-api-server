import functools
import logging
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


def get_jepl_files(config_json, composer_json, jenkinsfile):
    # Extract & parse special treatment properties
    ## JPL_DOCKER* envvars
    for srv_name, srv_data in composer_json['services'].items():
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
