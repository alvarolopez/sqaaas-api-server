import copy
import namegenerator

from jinja2 import Environment, PackageLoader, select_autoescape


class JePLUtils(object):
    """Class that generates JePL configuration files."""
    def generate_file_name(file_type, random=False):
        """Generates a file name for any of the JePL-related types of file

        :param file_type: Type of JePL file, one of [config, composer, jenkinsfile].
        :param random: Boolean that marks whether a random string should be inserted in the file name.
        """
        file_type_chunks = {
            'config': ['.sqa/config', 'yml'],
            'composer': ['.sqa/docker-compose', 'yml'],
            'jenkinsfile': ['Jenkinsfile'],
            'commands_script': ['.sqa/script', 'sh']
        }
        chunk_list = copy.deepcopy(file_type_chunks[file_type])
        random_str = namegenerator.gen()
        chunk_list.insert(1, random_str)

        return '.'.join(chunk_list)

    @classmethod
    def append_file_name(cls, file_type, file_data_list, force_random_name=False):
        """Appends a 'file_name' property, according to its type (file_type),
        to each Dict element of the given List (file_data_list)

        :param cls: Current class (from classmethod)
        :param file_type: Type of JePL file, one of [config, composer, jenkinsfile].
        :param file_data_list: List of JSON payload data to be associated with the generated file name.
        :param force_random_name: If set the method will always return a random name for the file.
        """
        new_file_data_list = []
        count = 0
        for data in file_data_list:
            if count > 0 or force_random_name:
                file_name = cls.generate_file_name(file_type, random=True)
            else:
                file_name = cls.generate_file_name(file_type)
            new_data = copy.deepcopy(data)
            new_data.update({'file_name': file_name})
            new_file_data_list.append(new_data)
            count += 1

        return new_file_data_list

    @staticmethod
    def get_commands_script(checkout_dir, cmd_list):
        """Returns a String with the 'commands' builder script.

        :param checkout_dir: Directory to chdir to run the script
        :param cmd_list: List of commands from the builder
        """
        env = Environment(
            loader=PackageLoader('openapi_server', 'templates')
        )
        template = env.get_template('commands_script.sh')
        return template.render({
            'checkout_dir': checkout_dir,
            'commands': '&&'.join(cmd_list)
        })

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
