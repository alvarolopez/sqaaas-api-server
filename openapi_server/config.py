import logging
import sys

from configparser import ConfigParser


logger = logging.getLogger('sqaaas_api.config')

CONF_FILE = '/etc/sqaaas/sqaaas.ini' # FIXME get this through argparse
CI_SECTION = 'jenkins'


def init():
    global CONF
    global REPO_BACKEND

    CONF = ConfigParser()
    config_exists = CONF.read(CONF_FILE)
    if not config_exists:
        logger.error('Configuration file <%s> does not exist' % CONF_FILE)
        sys.exit(1)
    REPO_BACKEND = CONF.defaults()['repository_backend']


def get_repo(key, fallback=None):
    return CONF.get(REPO_BACKEND, key, fallback=fallback)


def get_ci(key, fallback=None):
    return CONF.get(CI_SECTION, key, fallback=fallback)
