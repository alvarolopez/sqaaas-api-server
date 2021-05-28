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

    def get_repo_content(self, repo_name, branch, path='.'):
        """Gets the repository content from the given branch.

        Returns a List of ContentFile objects.

        :param repo_name: Name of the repo (format: <user|org>/<repo_name>)
        :param branch: Name of the branch
        """
        repo = self.get_org_repository(repo_name)
        return repo.get_dir_contents(path, ref=branch)

    def get_file(self, file_name, repo_name, branch):
        """Gets the file's content from a GitHub repository.

        Returns a ContentFile object.

        :param file_name: Name of the file
        :param repo_name: Name of the repo (format: <user|org>/<repo_name>)
        :param branch: Name of the branch
        """
        repo = self.get_org_repository(repo_name)
        try:
            return repo.get_contents(file_name, ref=branch)
        except (UnknownObjectException, GithubException):
            return False

    def push_file(self, file_name, file_data, commit_msg, repo_name, branch):
        """Pushes a file into GitHub repository.

        Returns the commit ID (SHA format).

        :param file_name: Name of the affected file
        :param file_data: Contents of the file
        :param commit_msg: Message to use in the commit
        :param repo_name: Name of the repo to push (format: <user|org>/<repo_name>)
        :param branch: Branch to push
        """
        repo = self.get_org_repository(repo_name)
        contents = self.get_file(file_name, repo_name, branch)
        r = {}
        if contents:
            self.logger.debug('File <%s> already exists in the repository, updating..' % file_name)
            r = repo.update_file(contents.path, commit_msg, file_data, contents.sha, branch)
        else:
            self.logger.debug('File <%s> does not currently exist in the repository, creating..' % file_name)
            r = repo.create_file(file_name, commit_msg, file_data, branch)
        return r['commit'].sha

    def delete_file(self, file_name, repo_name, branch):
        """Pushes a file into GitHub repository.

        Returns the commit ID (SHA format).

        :param file_name: Name of the affected file
        :param repo_name: Name of the repo to push (format: <user|org>/<repo_name>)
        :param branch: Branch to push
        """
        commit_msg = 'Delete %s file' % file_name
        repo = self.get_org_repository(repo_name)
        contents = self.get_file(file_name, repo_name, branch)
        if contents:
            repo.delete_file(contents.path, commit_msg, contents.sha, branch)
            self.logger.debug('File %s deleted from repository <%s>' % (file_name, repo_name))

    def create_branch(self, repo_name, branch_name, head_branch_name):
        """Creates a branch in the given Github repository.

        Returns a Repository object.

        :param repo_name: Name of the repo to push (format: <user|org>/<repo_name>)
        :param branch_name: Name of the branch to create
        :param head_branch_name: Name of the branch to do the checkout from
        """
        repo = self.get_repository(repo_name)
        head_branch = repo.get_branch(head_branch_name)
        repo.create_git_ref(
            ref='refs/heads/' + branch_name,
            sha=head_branch.commit.sha)
        return repo

    def create_fork(self, upstream_repo_name, upstream_branch_name=None, org_name='eosc-synergy'):
        """Creates a fork in the given Github organization.

        Returns a Repository object.

        :param upstream_repo_name: Name of the remote repo to fork (format: <user|org>/<repo_name>)
        :param upstream_branch_name: Name of the remote branch to fork
        :param org_name: Name of the Github organization to where the repo will be forked
        """
        upstream_repo = self.get_repository(upstream_repo_name)
        fork = None
        # fork_default_branch = 'sqaaas'
        upstream_org_name = upstream_repo_name.split('/')[0]

        if upstream_org_name.lower() in [org_name]:
            self.logger.debug('Upstream organization matches the target organization <%s>' % org_name)
        else:
            # if upstream_branch_name:
            #     _branch_source = upstream_branch_name
            # else:
            #     _branch_source = upstream_repo.raw_data['default_branch']
            # _branch_target = fork_default_branch
            # try:
            #     if upstream_repo.get_branch(_branch_target):
            #         self.logger.debug('Branch <%s> already exists in fork' % _branch_target)
            # except GithubException:
            #     self.logger.debug('Branch <%s> does not exist in fork' % _branch_target)
            #     self.logger.debug('Creating <%s> branch from source branch <%s>' % (_branch_target, _branch_source))
            #     _branch_source_obj = upstream_repo.get_branch(_branch_source)
            #     upstream_repo.create_git_ref(
            #         ref='refs/heads/' + _branch_target,
            #         sha=_branch_source_obj.commit.sha)
            # fork = upstream_repo

            org = self.client.get_organization(org_name)
            fork = org.create_fork(upstream_repo)

            # _fork_parent = fork.raw_data['parent']['owner']['login']
            # if _fork_parent not in [upstream_org_name]:
            #     self.logger.error('Repository (fork) already exists in <%s> organization. Removing..' % org_name)
            #     raise GithubException(status=422, data={'message': 'Reference (fork) already exists'})
            # else:
            #     self.logger.debug('New fork created: %s' % fork.raw_data['full_name'])
            # fork_default_branch = fork.raw_data['parent']['default_branch']

        # return (fork.raw_data['full_name'], fork_default_branch)
        return fork

    def create_pull_request(self,
                            repo_name, branch_name,
                            upstream_repo_name, upstream_branch_name=None):
        """Creates a pull request in the given upstream repository.

        Returns a Repository object.

        :param repo_name: Name of the source repository (format: <user|org>/<repo_name>)
        :param branch_name: Name of the source branch
        :param upstream_repo_name: Name of the remote repo to fork (format: <user|org>/<repo_name>)
        :param upstream_branch_name: Name of the remote branch to fork
        """
        upstream_repo = self.get_repository(upstream_repo_name)
        if not upstream_branch_name:
            upstream_branch_name = upstream_repo.default_branch
            self.logger.debug(('Branch not defined for the upstream repository. '
                               'Using default: %s' % upstream_branch_name))
        body = '''
        Add JePL folder structure via SQAaaS.

        FILES
          - [x] .sqa/config.yml
          - [x] .sqa/docker-compose.yml
          - [x] Jenkinsfile
        '''
        _repo_org = repo_name.split('/')[0]
        head = ':'.join([_repo_org, branch_name])

        self.logger.debug('Creating pull request: %s (head) -> %s (base)' % (
            head, upstream_branch_name))
        pr = upstream_repo.create_pull(
            title='Add CI/CD pipeline (JePL) in project <%s>' % upstream_repo_name,
            body=body,
            head=head,
            base=upstream_branch_name)
        self.logger.debug(('Pull request successfully created: %s (head) -> %s '
                           '(base)' % (head, upstream_branch_name)))
        return pr.raw_data

    def get_repository(self, repo_name):
        """Return a Repository from a GitHub repo if it exists, False otherwise.

        :param repo_name: Name of the repo (format: <user|org>/<repo_name>)
        """
        repo = False
        try:
            repo = self.client.get_repo(repo_name)
        except UnknownObjectException as e:
            self.logger.debug('Unknown Github exception: %s' % e)
        finally:
            if repo:
                self.logger.debug('Repository <%s> found' % repo_name)
            else:
                self.logger.debug('Repository <%s> not found!' % repo_name)
        return repo

    def get_org_repository(self, repo_name, org_name='eosc-synergy'):
        """Gets a repository from the given Github organization.

        If found, it returns the repo object, otherwise False

        :param repo_name: Name of the repo (format: <user|org>/<repo_name>)
        """
        _org_name, _repo_name = repo_name.split('/')
        org = self.client.get_organization(_org_name)
        try:
            return org.get_repo(_repo_name)
        except UnknownObjectException:
            return False

    def create_org_repository(self, repo_name):
        """Creates a GitHub repository for the current organization.

        Returns the Repository object.

        :param repo_name: Name of the repo (format: <user|org>/<repo_name>)
        """
        _org_name, _repo_name = repo_name.split('/')
        repo = self.get_org_repository(repo_name)
        if not repo:
            org = self.client.get_organization(_org_name)
            repo = org.create_repo(_repo_name)
            self.logger.debug('GitHub repository <%s> does not exist, creating..' % repo_name)
        else:
            self.logger.debug('GitHub repository <%s> already exists' % repo_name)
        return repo

    def delete_repo(self, repo_name):
        """Delete a GitHub repository.

        :param repo_name: Name of the repo (format: <user|org>/<repo_name>)
        """
        repo = self.get_org_repository(repo_name)
        self.logger.debug('Deleting repository: %s' % repo_name)
        repo.delete()
        self.logger.debug('Repository <%s> successfully deleted' % repo_name)

    def get_commit_url(self, repo_name, commit_id):
        """Returns the commit URL (HTML format) that corresponds to the given commit ID.

        :param repo_name: Name of the repo (format: <user|org>/<repo_name>)
        :param commit_id: SHA-based ID for the commit
        """
        repo = self.get_org_repository(repo_name)
        self.logger.debug('Getting commit data for SHA <%s>' % commit_id)
        return repo.get_commit(commit_id).html_url
