import argparse
import connexion
import os
import logging

from openapi_server import config


def set_log():
    logger = logging.getLogger('sqaaas_api')
    logger.setLevel(logging.DEBUG)
    ch = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    ch.setFormatter(formatter)
    logger.addHandler(ch)


def set_parser():
    parser = argparse.ArgumentParser(description='SQAaaS API server.')
    parser.add_argument(
        '-c',
        '--config',
        metavar='CONFIG_FILE',
        dest='config_file',
        default='/etc/sqaaas/sqaaas.ini',
        help='Main configuration file (default: /etc/sqaaas/sqaaas.ini)')

    return parser.parse_args()


def main():
    options_cli = set_parser()
    options = {
        "swagger_ui": True
    }

    set_log()
    config.init(options_cli.config_file)

    specification_dir = os.path.join(os.path.dirname(__file__), 'openapi')
    app = connexion.AioHttpApp(__name__, specification_dir=specification_dir, options=options)
    app.add_api('openapi.yaml',
                arguments={'title': 'SQAaaS API'},
                pythonic_params=True,
                pass_context_arg_name='request')
    app.run(port=8080)
