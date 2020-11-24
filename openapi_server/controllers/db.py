import json
import logging
import os


DB_FILE = '/sqaaas/sqaaas.json'
logger = logging.getLogger('sqaaas_api.controller.db')


def load_content():
    data = {}
    if os.path.exists(DB_FILE) and os.stat(DB_FILE).st_size > 0:
        with open(DB_FILE) as db:
            data = json.load(db)
    return data


def store_content(data):
    with open(DB_FILE, 'w') as db:
        json.dump(data, db)
    print_content()


def print_content():
    db = load_content()
    logger.debug('Current DB content: %s' % list(db))
