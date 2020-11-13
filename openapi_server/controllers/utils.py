import logging

from openapi_server.controllers.jepl import JePLUtils


logger = logging.getLogger('sqaaas_api.controller')


def get_jepl_files(config_json, composer_json, jenkinsfile):
    config_yml, composer_yml = JePLUtils.get_sqa_files(
        config_json,
        composer_json)
    jenkinsfile = JePLUtils.get_jenkinsfile(jenkinsfile)

    return (config_yml, composer_yml, jenkinsfile)


def push_jepl_files(gh_utils, repo, config_json, composer_json, jenkinsfile):
    config_yml, composer_yml, jenkinsfile = get_jepl_files(
        config_json,
        composer_json,
        jenkinsfile)
    logger.debug('Pushing file to GitHub repository <%s>: .sqa/config.yml' % repo)
    gh_utils.push_file('.sqa/config.yml', config_yml, 'Update config.yml', repo)
    logger.debug('Pushing file to GitHub repository <%s>: .sqa/docker-compose.yml' % repo)
    gh_utils.push_file('.sqa/docker-compose.yml', composer_yml, 'Update docker-compose.yml', repo)
    logger.debug('Pushing file to GitHub repository <%s>: Jenkinsfile' % repo)
    gh_utils.push_file('Jenkinsfile', jenkinsfile, 'Update Jenkinsfile', repo)
    logger.info('GitHub repository <%s> created with the JePL file structure' % repo)
