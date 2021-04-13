import copy
import json
import logging
import pathlib

from openapi_server import config
from openapi_server.controllers import utils as ctls_utils


DB_FILE = pathlib.Path(
    config.get('db_file', fallback='/sqaaas/sqaaas.json'))
logger = logging.getLogger('sqaaas_api.controller.db')


def load_content():
    data = {}
    if DB_FILE.exists():
        data = json.loads(DB_FILE.read_text(encoding='utf-8'))
    return data


def store_content(data):
    try:
        DB_FILE.parent.mkdir(parents=True, exist_ok=False)
    except FileExistsError:
        logger.debug('DB file path: parent folder already exists')
    else:
        logger.debug('DB file path: parent folder created')

    DB_FILE.write_text(json.dumps(data), encoding='utf-8')


def print_content():
    db = load_content()
    logger.debug('Current DB content: %s' % list(db))


def add_entry(pipeline_id, pipeline_repo, body):
    """Adds a standard entry in the DB.

    Each entry has both the raw data from the request and the
    processed data, as treated internally by the API. An entry
    is indexed by the pipeline ID

    |-- <pipeline_id>: ID of the pipeline
        |-- 'pipeline_repo': [String] Name of the repository in the remote platform.
        |-- 'data': [Dict] Internal representation of the data.
            |-- 'config': [List] Each independent JePL-compliant config data.
                |-- 'data_json'
                |-- 'data_yml'
                |-- 'data_when'
                |-- 'file_name'
            |-- 'composer': [Dict] JePL-compliant composer data.
                |-- 'data_json'
                |-- 'data_yml'
                |-- 'file_name'
            |-- 'jenkinsfile': [String] Jenkins-compliant pipeline.
        |-- 'raw_request': [Dict] API spec representation (from JSON request).

    :param pipeline_id: UUID-format identifier for the pipeline.
    :param pipeline_repo: URL of the remote repository for the Jenkins integration.
    :param body: Raw JSON coming from the HTTP request.
    """
    raw_request = copy.deepcopy(body)
    config_json, composer_json, jenkinsfile_data = ctls_utils.get_pipeline_data(body)
    config_data_list, composer_data, jenkinsfile = ctls_utils.get_jepl_files(
        config_json, composer_json
    )

    db = load_content()
    db[pipeline_id] = {
        'pipeline_repo': pipeline_repo,
        'data': {
            'config': config_data_list,
            'composer': composer_data,
            'jenkinsfile': jenkinsfile
        },
        'raw_request': raw_request
    }
    store_content(db)


def get_entry(pipeline_id):
    """Returns the given pipeline ID entry from the DB.

    :param pipeline_id: UUID-format identifier for the pipeline.
    """
    db = load_content()
    logger.debug('Loading pipeline <%s> from DB' % pipeline_id)

    return db[pipeline_id]
