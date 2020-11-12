import logging

from github import Github
from github.GithubException import GithubException
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
        self.logger = logging.getLogger('sqaaas_api.github')

    def get_org_repository(self, repo_name, org_name='eosc-synergy'):
        org = self.client.get_organization(org_name)
        try:
            return org.get_repo(repo_name)
        except UnknownObjectException:
            return False

    def get_repo_content(self, repo_name, file_name=''):
        repo = self.client.get_repo(repo_name)
        try:
            return repo.get_contents(file_name)
        except (UnknownObjectException, GithubException):
            return False

    def push_file(self, file_name, file_data, commit_msg, repo_name):
        repo = self.client.get_repo(repo_name)
        contents = self.get_repo_content(repo_name, file_name)
        if contents:
            repo.update_file(contents.path, commit_msg, file_data, contents.sha)
            self.logger.debug('File <%s> does not currently exist in the repository, creating..' % file_name)
        else:
            repo.create_file(file_name, commit_msg, file_data)
            self.logger.debug('File <%s> already exist in the repository, updating..' % file_name)

    def create_fork(self, upstream_repo_name, org_name='eosc-synergy'):
        repo_name = upstream_repo_name.split('/')[-1]
        self.logger.debug('Obtained repo name from the upstream one: %s' % repo_name)
        fork = self.get_org_repository(repo_name, org_name=org_name)
        if fork:
            self.logger.debug('Repository (fork) already exists in <%s> organization. Removing..' % org_name)
            fork.delete()
            self.logger.debug('Repository (fork) removed from <%s> organization' % org_name)
        org = self.client.get_organization(org_name)
        repo = self.client.get_repo(upstream_repo_name)
        fork = org.create_fork(repo)
        self.logger.debug('New fork created: %s' % fork.raw_data['full_name'])
        return fork.raw_data

    def create_pull_request(self, upstream_repo_name, repo_name, upstream_branch='master', branch='master'):
        repo = self.client.get_repo(upstream_repo_name)
        body = '''
        Add JePL folder structure via SQAaaS.

        FILES
          - [x] .sqa/config.yml
          - [x] .sqa/docker-compose.yml
          - [x] Jenkinsfile
        '''
        _repo_org = repo_name.split('/')[0]
        head = ':'.join([_repo_org, branch])
        pr = repo.create_pull(
            title='Set up JePL in project <%s>' % upstream_repo_name,
            body=body,
            head=head,
            base=upstream_branch)
        self.logger.debug('Pull request created: %s (head) -> %s (base)' % (head, upstream_branch))
        return pr.raw_data

    def get_repository(self, repo_name):
        try:
            repo = self.client.get_repo(repo_name)
            self.logger.debug('Repository <%s> found' % repo_name)
            return repo.raw_data
        except UnknownObjectException:
            self.logger.debug('Repository <%s> not found!' % repo_name)
            return False

    def create_org_repository(self, repo_name):
        _org_name, _repo_name = repo_name.split('/')
        if not self.get_org_repository(repo_name):
            org = self.client.get_organization(_org_name)
            repo = org.create_repo(_repo_name)
            self.logger.debug('GitHub repository <%s> does not exist, creating..' % repo_name)
        else:
            self.logger.debug('GitHub repository <%s> already exists' % repo_name)
