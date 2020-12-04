import argparse
import connexion
import os
import logging

from openapi_server import config


def set_log(debug=False):
    logger = logging.getLogger('sqaaas_api')
    logger.setLevel(logging.DEBUG if debug else logging.INFO)
    ch = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    ch.setFormatter(formatter)
    logger.addHandler(ch)


def set_parser():
    parser = argparse.ArgumentParser(description='SQAaaS API server.')
    current_folder = os.path.dirname(os.path.realpath(__file__))
    sample_config = os.path.join(
        os.path.dirname(current_folder), 'etc/sqaaas.ini.sample')
    parser.add_argument(
        '-c',
        '--config',
        metavar='CONFIG_FILE',
        dest='config_file',
        default='/etc/sqaaas/sqaaas.ini',
        help='Main configuration file (default: /etc/sqaaas/sqaaas.ini). '
             'For a complete example, please check <%s>' % sample_config)
    parser.add_argument(
        '-p',
        '--port',
        metavar='PORT',
        dest='port',
        default='8080',
        help='Port number to be used when exposing the API server')
    parser.add_argument(
        '-d',
        '--debug',
        action="store_true",
        help='Set DEBUG log level')

    return parser.parse_args()


def main():
    options_cli = set_parser()
    options = {
        "swagger_ui": True
    }

    set_log(options_cli.debug)
    config.init(options_cli.config_file)

    specification_dir = os.path.join(os.path.dirname(__file__), 'openapi')
    app = connexion.AioHttpApp(__name__, specification_dir=specification_dir, options=options)
    app.add_api('openapi.yaml',
                arguments={'title': 'SQAaaS API'},
                pythonic_params=True,
                pass_context_arg_name='request')
    app.run(port=options_cli.port)
