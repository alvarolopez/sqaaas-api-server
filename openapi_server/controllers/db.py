import json
import logging
import pathlib

from openapi_server import config


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
    print_content()


def print_content():
    db = load_content()
    logger.debug('Current DB content: %s' % list(db))
