# coding: utf-8

from datetime import date, datetime

from typing import List, Dict, Type

from openapi_server.models.base_model_ import Model
from openapi_server.models.creds_user_pass import CredsUserPass
from openapi_server import util


class JePLConfigConfig(Model):
    """NOTE: This class is auto generated by OpenAPI Generator (https://openapi-generator.tech).

    Do not edit the class manually.
    """

    def __init__(self, project_repos: Dict[str, object]=None, credentials: List[CredsUserPass]=None):
        """JePLConfigConfig - a model defined in OpenAPI

        :param project_repos: The project_repos of this JePLConfigConfig.
        :param credentials: The credentials of this JePLConfigConfig.
        """
        self.openapi_types = {
            'project_repos': Dict[str, object],
            'credentials': List[CredsUserPass]
        }

        self.attribute_map = {
            'project_repos': 'project_repos',
            'credentials': 'credentials'
        }

        self._project_repos = project_repos
        self._credentials = credentials

    @classmethod
    def from_dict(cls, dikt: dict) -> 'JePLConfigConfig':
        """Returns the dict as a model

        :param dikt: A dict.
        :return: The JePL_config_config of this JePLConfigConfig.
        """
        return util.deserialize_model(dikt, cls)

    @property
    def project_repos(self):
        """Gets the project_repos of this JePLConfigConfig.


        :return: The project_repos of this JePLConfigConfig.
        :rtype: Dict[str, object]
        """
        return self._project_repos

    @project_repos.setter
    def project_repos(self, project_repos):
        """Sets the project_repos of this JePLConfigConfig.


        :param project_repos: The project_repos of this JePLConfigConfig.
        :type project_repos: Dict[str, object]
        """

        self._project_repos = project_repos

    @property
    def credentials(self):
        """Gets the credentials of this JePLConfigConfig.


        :return: The credentials of this JePLConfigConfig.
        :rtype: List[CredsUserPass]
        """
        return self._credentials

    @credentials.setter
    def credentials(self, credentials):
        """Sets the credentials of this JePLConfigConfig.


        :param credentials: The credentials of this JePLConfigConfig.
        :type credentials: List[CredsUserPass]
        """

        self._credentials = credentials
