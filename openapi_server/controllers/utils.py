import copy
import functools
import itertools
import logging
import re
import uuid
import yaml

from aiohttp import web
from urllib.parse import urlparse

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


def debug_request(f):
    @functools.wraps(f)
    async def decorated_function(*args, **kwargs):
        logger.debug('Received request (keyword args): %s' % kwargs)
        ret = await f(*args, **kwargs)
        return ret
    return decorated_function


def extended_data_validation(f):
    @functools.wraps(f)
    async def decorated_function(*args, **kwargs):
        body = kwargs['body']
        config_data_list = body['config_data']
        composer_data = body['composer_data']
        # Validate pipeline name
        if re.search(r'[^-.\w]', body['name']):
            _reason = 'Invalid pipeline name (allowed characters: [A-Za-z0-9_.-])'
            logger.warning(_reason)
            return web.Response(status=400, reason=_reason)
        # Check if registry>push, then registry>credential_id
        do_docker_push = False
        for srv_name, srv_data in composer_data['services'].items():
            try:
                registry_data = srv_data['image']['registry']
                if registry_data['push'] and not registry_data['credential_id']:
                    _reason = 'Request to push Docker images, but no credentials provided!'
                    logger.warning(_reason)
                    return web.Response(status=400, reason=_reason)
            except KeyError as e:
                continue

        ret = await f(*args, **kwargs)
        return ret
    return decorated_function


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


def json_to_yaml(json_data):
    """Returns the YAML translation of the incoming JSON payload.

    :param json_data: JSON payload.
    """
    return yaml.dump(json_data)


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
    """Manage those properties, present in the API spec, that cannot
    be directly translated into a workable 'config.yml' or composer
    (i.e. 'docker-compose.yml).

    This method returns:
    - 'config_json_list' is a JSON List of Dicts {'data_json': <data>,
                                                    'data_when': <data>}
    - 'composer_json' is a JSON Dict
    - 'commands_script_list' is a list of strings to generate the command builder scripts

    :param config_json: JePL's config as received through the API request (JSON payload)
    :param composer_json: Composer content as received throught the API request (JSON payload).
    """
    # COMPOSER (Docker Compose specific)
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
        ## Set 'volumes' property (incl. default values)
        try:
            srv_data['volumes']
        except KeyError:
            pass
        else:
            srv_data['volumes'] = [{
                'type': 'bind',
                'source': './',
                'target': '/sqaaas-build'
            }]
        ## Set 'working_dir' property (for simple use cases)
        ## NOTE Setting working_dir only makes sense when only one volume is expected!
        srv_data['working_dir'] = srv_data['volumes'][0]['target']
        ## Check for empty values
        props_to_remove = []
        for prop, prop_value in srv_data.items():
            pop_prop = False
            if isinstance(prop_value, dict):
                if not any(prop_value.values()):
                    pop_prop = True
            elif isinstance(prop_value, (list, str)):
                if not prop_value:
                    pop_prop = True
            if pop_prop:
                props_to_remove.append(prop)
        [srv_data.pop(prop) for prop in props_to_remove]

    composer_data = {'data_json': composer_json}

    # CONFIG:CONFIG (Set repo name)
    project_repos_final = {}
    project_repos_mapping = {}
    if 'project_repos' in config_json['config'].keys():
        for project_repo in config_json['config']['project_repos']:
            repo_url = project_repo.pop('repo')
            repo_url_parsed = urlparse(repo_url)
            repo_name_generated = ''.join([
                repo_url_parsed.netloc,
                repo_url_parsed.path,
            ])
            project_repos_final[repo_name_generated] = {
                'repo': repo_url,
                **project_repo
            }
            project_repos_mapping[repo_url] = {
                'name': repo_name_generated,
                **project_repo
            }
        config_json['config']['project_repos'] = project_repos_final

    # CONFIG:SQA_CRITERIA (Multiple stages/Jenkins when clause, Array-to-Object transformation for repos)
    config_data_list = []
    commands_script_list = []
    config_json_no_when = copy.deepcopy(config_json)
    for criterion_name, criterion_data in config_json['sqa_criteria'].items():
        criterion_data_copy = copy.deepcopy(criterion_data)
        if 'repos' in criterion_data.keys():
            repos_old = criterion_data_copy.pop('repos')
            repos_new = {}
            for repo in repos_old:
                try:
                    repo_url = repo.pop('repo_url')
                    if not repo_url:
                        raise KeyError
                except KeyError:
                    # Use 'this_repo' as the placeholder for current repo & version
                    repos_new['this_repo'] = repo
                else:
                    repo_name = project_repos_mapping[repo_url]['name']
                    repos_new[repo_name] = repo
                    # Create script for 'commands' builder
                    # NOTE: This is a workaround -> a specific builder to tackle this will be implemented in JePL
                    if 'commands' in repo.keys():
                        commands_script_data = JePLUtils.get_commands_script(
                            repo_name,
                            repo['commands']
                        )
                        commands_script_data = JePLUtils.append_file_name(
                            'commands_script',
                            [{
                                'data': commands_script_data
                            }],
                            force_random_name=True
                        )
                        commands_script_list.extend(commands_script_data)
                        script_call = '/usr/bin/env sh %s' % commands_script_data[0]['file_name']
                        repos_new[repo_name]['commands'] = [script_call]
            criterion_data_copy['repos'] = repos_new
        if 'when' in criterion_data.keys():
            config_json_when = copy.deepcopy(config_json)
            config_json_when['sqa_criteria'] = {
                criterion_name: criterion_data_copy
            }
            when_data = criterion_data_copy.pop('when')
            config_data_list.append({
		'data_json': config_json_when,
                'data_when': when_data
	    })
            config_json_no_when['sqa_criteria'].pop(criterion_name)
        else:
            config_json_no_when['sqa_criteria'][criterion_name] = criterion_data_copy

    if config_json_no_when['sqa_criteria']:
        config_data_list.append({
            'data_json': config_json_no_when,
            'data_when': None
        })

    return (config_data_list, composer_data, commands_script_list)
