from github import Github


class GitHubUtils(object):
    """Class for handling requests to GitHub API.

    Support only for token-based access.

    """
    def __init__(self, access_token=None):
        """GitHubUtils object definition.

        :param access_token: GitHub's access token
        """
        self.client = GitHub(self.access_token)

    def get_org_repository(org_name='eosc-synergy', repo_name):
        org = self.client.get_organization(org_name)
        return org.get_repo(repo_name.raw_data)

    def create_org_repository(org_name='eosc-synergy', repo_name):
        org = self.client.get_organization(org_name)
        repo = org.create_repo(repo_name)
