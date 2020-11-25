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

    def get_repo_content(self, repo_name, file_name, branch):
        repo = self.client.get_repo(repo_name)
        try:
            return repo.get_contents(file_name, ref=branch)
        except (UnknownObjectException, GithubException):
            return False

    def push_file(self, file_name, file_data, commit_msg, repo_name, branch='sqaaas'):
        repo = self.client.get_repo(repo_name)
        contents = self.get_repo_content(repo_name, file_name, branch)
        if contents:
            self.logger.debug('File <%s> already exists in the repository, updating..' % file_name)
            repo.update_file(contents.path, commit_msg, file_data, contents.sha, branch=branch)
        else:
            self.logger.debug('File <%s> does not currently exist in the repository, creating..' % file_name)
            repo.create_file(file_name, commit_msg, file_data, branch=branch)

    def create_fork(self, upstream_repo_name, org_name='eosc-synergy'):
        repo = self.client.get_repo(upstream_repo_name)
        fork = None
        fork_default_branch = 'sqaaas'
        upstream_org_name, repo_name = upstream_repo_name.split('/')
        if upstream_org_name.lower() == org_name:
            self.logger.debug('Upstream organization matches the target organization <%s>' % org_name)
            _branch_source = repo.raw_data['default_branch']
            _branch_target = fork_default_branch
            if repo.get_branch(_branch_target):
                self.logger.debug('Branch <%s> already exists in fork' % _branch_target)
            else:
                self.logger.debug('Creating <%s> branch from source branch <%s>' % (_branch_target, _branch_source))
                _branch_source_obj = repo.get_branch(_branch_source)
                repo.create_git_ref(
                    ref='refs/heads/' + _branch_target,
                    sha=_branch_source_obj.commit.sha)
            fork = repo
        else:
            org = self.client.get_organization(org_name)
            fork = org.create_fork(repo)
            _fork_parent = fork.raw_data['parent']['owner']['login']
            if _fork_parent not in [upstream_org_name]:
                self.logger.error('Repository (fork) already exists in <%s> organization. Removing..' % org_name)
                raise GithubException(status=422, data={'message': 'Reference (fork) already exists'})
            else:
                self.logger.debug('New fork created: %s' % fork.raw_data['full_name'])
            fork_default_branch = fork.raw_data['parent']['default_branch']

        return (fork.raw_data['full_name'], fork_default_branch)

    def create_pull_request(self, upstream_repo_name, repo_name, branch, upstream_branch='master'):
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
        self.logger.debug('Creating pull request: %s (head) -> %s (base)' % (head, upstream_branch))
        pr = repo.create_pull(
            title='Set up JePL in project <%s>' % upstream_repo_name,
            body=body,
            head=head,
            base=upstream_branch)
        self.logger.debug('Pull request successfully created: %s (head) -> %s (base)' % (head, upstream_branch))
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
