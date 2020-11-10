from openapi_server.controllers.jepl import JePLUtils


def get_jepl_files(config_json, composer_json, jenkinsfile):
    config_yml, composer_yml = JePLUtils.get_sqa_files(
        config_json,
        composer_json)
    jenkinsfile = JePLUtils.get_jenkinsfile(jenkinsfile)

    return (config_yml, composer_yml, jenkinsfile)
