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

    def get_repo_content(self, repo_name, branch, path='.'):
        """Gets the repository content from the given branch.

        Returns a List of ContentFile objects.

        :param repo_name: Name of the repo (format: <user|org>/<repo_name>)
        :param branch: Name of the branch
        """
        repo = self.client.get_repo(repo_name)
        return repo.get_dir_contents(path, ref=branch)

    def get_file(self, file_name, repo_name, branch):
        """Gets the file's content from a GitHub repository.

        Returns a ContentFile object.

        :param file_name: Name of the file
        :param repo_name: Name of the repo (format: <user|org>/<repo_name>)
        :param branch: Name of the branch
        """
        repo = self.client.get_repo(repo_name)
        try:
            return repo.get_contents(file_name, ref=branch)
        except (UnknownObjectException, GithubException):
            return False

    def push_file(self, file_name, file_data, commit_msg, repo_name, branch='sqaaas'):
        """Pushes a file into GitHub repository.

        Returns the commit ID (SHA format).

        :param file_name: Name of the affected file
        :param file_data: Contents of the file
        :param commit_msg: Message to use in the commit
        :param repo_name: Name of the repo to push (format: <user|org>/<repo_name>)
        :param branch: Branch to push
        """
        repo = self.client.get_repo(repo_name)
        contents = self.get_file(file_name, repo_name, branch)
        r = {}
        if contents:
            self.logger.debug('File <%s> already exists in the repository, updating..' % file_name)
            r = repo.update_file(contents.path, commit_msg, file_data, contents.sha, branch=branch)
        else:
            self.logger.debug('File <%s> does not currently exist in the repository, creating..' % file_name)
            r = repo.create_file(file_name, commit_msg, file_data, branch=branch)
        return r['commit'].sha

    def delete_file(self, file_name, repo_name, branch='sqaaas'):
        """Pushes a file into GitHub repository.

        Returns the commit ID (SHA format).

        :param file_name: Name of the affected file
        :param repo_name: Name of the repo to push (format: <user|org>/<repo_name>)
        :param branch: Branch to push
        """
        commit_msg = 'Delete %s file' % file_name
        repo = self.client.get_repo(repo_name)
        contents = self.get_file(file_name, repo_name, branch)
        if contents:
            repo.delete_file(contents.path, commit_msg, contents.sha, branch=branch)
            self.logger.debug('File %s deleted from repository <%s>' % (file_name, repo_name))

    def create_fork(self, upstream_repo_name, upstream_branch_name=None, org_name='eosc-synergy'):
        """Creates a fork in the given Github organization.

        Returns a tuple with the fork repo and branch created.

        :param upstream_repo_name: Name of the remote repo to fork (format: <user|org>/<repo_name>)
        :param upstream_branch_name: Name of the remote branch to fork
        :param org_name: Name of the Github organization to where the repo will be forked
        """
        upstream_repo = self.client.get_repo(upstream_repo_name)
        fork = None
        fork_default_branch = 'sqaaas'
        upstream_org_name = upstream_repo_name.split('/')[0]

        if upstream_org_name.lower() == org_name:
            self.logger.debug('Upstream organization matches the target organization <%s>' % org_name)
            if upstream_branch_name:
                _branch_source = upstream_branch_name
            else:
                _branch_source = upstream_repo.raw_data['default_branch']
            _branch_target = fork_default_branch
            try:
                if upstream_repo.get_branch(_branch_target):
                    self.logger.debug('Branch <%s> already exists in fork' % _branch_target)
            except GithubException:
                self.logger.debug('Branch <%s> does not exist in fork' % _branch_target)
                self.logger.debug('Creating <%s> branch from source branch <%s>' % (_branch_target, _branch_source))
                _branch_source_obj = upstream_repo.get_branch(_branch_source)
                upstream_repo.create_git_ref(
                    ref='refs/heads/' + _branch_target,
                    sha=_branch_source_obj.commit.sha)
            fork = upstream_repo
        else:
            org = self.client.get_organization(org_name)
            fork = org.create_fork(upstream_repo)
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
        """Return raw data from a GitHub repository.

        :param repo_name: Name of the repo (format: <user|org>/<repo_name>)
        """
        try:
            repo = self.client.get_repo(repo_name)
            self.logger.debug('Repository <%s> found' % repo_name)
            return repo.raw_data
        except UnknownObjectException:
            self.logger.debug('Repository <%s> not found!' % repo_name)
            return False

    def create_org_repository(self, repo_name):
        """Creates a GitHub repository for the current organization.

        Returns the repository full name.

        :param repo_name: Name of the repo (format: <user|org>/<repo_name>)
        """
        _org_name, _repo_name = repo_name.split('/')
        if not self.get_org_repository(repo_name):
            org = self.client.get_organization(_org_name)
            repo = org.create_repo(_repo_name)
            self.logger.debug('GitHub repository <%s> does not exist, creating..' % repo_name)
        else:
            self.logger.debug('GitHub repository <%s> already exists' % repo_name)
            return False
        return repo.raw_data['full_name']

    def delete_repo(self, repo_name):
        """Delete a GitHub repository.

        :param repo_name: Name of the repo (format: <user|org>/<repo_name>)
        """
        repo = self.client.get_repo(repo_name)
        self.logger.debug('Deleting repository: %s' % repo_name)
        repo.delete()
        self.logger.debug('Repository <%s> successfully deleted' % repo_name)

    def get_commit_url(self, repo_name, commit_id):
        """Returns the commit URL (HTML format) that corresponds to the given commit ID.

        :param repo_name: Name of the repo (format: <user|org>/<repo_name>)
        :param commit_id: SHA-based ID for the commit
        """
        repo = self.client.get_repo(repo_name)
        self.logger.debug('Getting commit data for SHA <%s>' % commit_id)
        return repo.get_commit(commit_id).html_url
