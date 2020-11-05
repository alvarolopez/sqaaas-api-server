import json
import yaml

from jinja2 import Environment, PackageLoader, select_autoescape


class JePLUtils(object):
    """Class that generates JePL configuration files."""
    @staticmethod
    def get_sqa_files(config_data, composer_data):
        """Returns the YAML translation of the incoming JSON payload.

        :param config_data: JSON payload with the main config content.
        :param composer_data: JSON payload with the composer content.
        """
        yaml_data_list = []
        for data in [config_data, composer_data]:
            # json_data = json.load(data)
            # yaml_data_list.append(yaml.dump(json_data))
            yaml_data_list.append(yaml.dump(data))

        return yaml_data_list

    @staticmethod
    def get_jenkinsfile(jenkinsfile_data):
        """Returns the Jenkinsfile from the incoming JSON payload.

        :param jenkinsfile_data: JSON payload with the Jenkinsfile content.
        """
        env = Environment(
            loader=PackageLoader('openapi_server', 'templates')
        )
        template = env.get_template('Jenkinsfile')

        return template.render()
