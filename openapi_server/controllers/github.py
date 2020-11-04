import logging

from github import Github
from github.GithubException import UnknownObjectException


class GitHubUtils(object):
    """Class for handling requests to GitHub API.

    Support only for token-based access.
    """
    def __init__(self, access_token):
        """GitHubUtils object definition.

        :param access_token: GitHub's access token
        """
        self.client = Github(access_token)
        self.logger = logging.getLogger('sqaaas_api.github.GitHubUtils')
        self.logger.info('Hello from GitHubUtils class')

    def get_org_repository(self, repo_name, org_name='eosc-synergy'):
        org = self.client.get_organization(org_name)
        try:
            return org.get_repo(repo_name).raw_data
        except UnknownObjectException:
            return False

    def create_org_repository(self, repo_name, org_name='eosc-synergy'):
        org = self.client.get_organization(org_name)
        repo = org.create_repo(repo_name)
