# coding: utf-8

from datetime import date, datetime

from typing import List, Dict, Type

from openapi_server.models.base_model_ import Model
from openapi_server.models.criterion_build import CriterionBuild
from openapi_server.models.repository import Repository
from openapi_server import util


class JePLConfig(Model):
    """NOTE: This class is auto generated by OpenAPI Generator (https://openapi-generator.tech).

    Do not edit the class manually.
    """

    def __init__(self, project_repos: List[Repository]=None, sqa_criteria: List[CriterionBuild]=None):
        """JePLConfig - a model defined in OpenAPI

        :param project_repos: The project_repos of this JePLConfig.
        :param sqa_criteria: The sqa_criteria of this JePLConfig.
        """
        self.openapi_types = {
            'project_repos': List[Repository],
            'sqa_criteria': List[CriterionBuild]
        }

        self.attribute_map = {
            'project_repos': 'project_repos',
            'sqa_criteria': 'sqa_criteria'
        }

        self._project_repos = project_repos
        self._sqa_criteria = sqa_criteria

    @classmethod
    def from_dict(cls, dikt: dict) -> 'JePLConfig':
        """Returns the dict as a model

        :param dikt: A dict.
        :return: The JePL_config of this JePLConfig.
        """
        return util.deserialize_model(dikt, cls)

    @property
    def project_repos(self):
        """Gets the project_repos of this JePLConfig.


        :return: The project_repos of this JePLConfig.
        :rtype: List[Repository]
        """
        return self._project_repos

    @project_repos.setter
    def project_repos(self, project_repos):
        """Sets the project_repos of this JePLConfig.


        :param project_repos: The project_repos of this JePLConfig.
        :type project_repos: List[Repository]
        """

        self._project_repos = project_repos

    @property
    def sqa_criteria(self):
        """Gets the sqa_criteria of this JePLConfig.


        :return: The sqa_criteria of this JePLConfig.
        :rtype: List[CriterionBuild]
        """
        return self._sqa_criteria

    @sqa_criteria.setter
    def sqa_criteria(self, sqa_criteria):
        """Sets the sqa_criteria of this JePLConfig.


        :param sqa_criteria: The sqa_criteria of this JePLConfig.
        :type sqa_criteria: List[CriterionBuild]
        """

        self._sqa_criteria = sqa_criteria