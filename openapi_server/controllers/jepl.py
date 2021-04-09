import copy
import namegenerator

from jinja2 import Environment, PackageLoader, select_autoescape


class JePLUtils(object):
    """Class that generates JePL configuration files."""
    @staticmethod
    def append_file_name(file_type, file_data_list):
        """Appends a 'file_name' property, according to its type (file_type),
        to each Dict element of the given List (file_data_list)

        :param file_type: Type of JePL file, one of [config, composer, jenkinsfile].
        :param file_data_list: List of JSON payload data to be associated with the generated file name.
        """
        file_type_chunks = {
            'config': ['.sqa/config', 'yml'],
            'composer': ['.sqa/docker-compose', 'yml'],
            'jenkinsfile': ['Jenkinsfile']
        }

        new_file_data_list = []
        count = 0
        for data in file_data_list:
            chunk_list = copy.deepcopy(file_type_chunks[file_type])
            if count > 0:
                random_str = namegenerator.gen()
                chunk_list.insert(1, random_str)
            new_data = copy.deepcopy(data)
            new_data.update({'file_name': '.'.join(chunk_list)})
            new_file_data_list.append(new_data)
            count += 1

        return new_file_data_list

    @staticmethod
    def get_jenkinsfile(config_data_list):
        """Returns a String with the Jenkinsfile rendered from the given
        JSON payload.

        :param config_data_list: List of config data Dicts
        """
        env = Environment(
            loader=PackageLoader('openapi_server', 'templates')
        )
        template = env.get_template('Jenkinsfile')

        return template.render(config_data_list=config_data_list)
