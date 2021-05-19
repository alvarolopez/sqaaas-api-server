import logging
import os
import stat
import tempfile

from git import Repo
from git.exc import GitCommandError


REMOTE_NAME = 'sqaaas'


class GitUtils(object):
    """Class for handling Git commands.

    Authentication done via askpass helper.
    """
    def __init__(self, access_token):
        """GitUtils object definition.

        :param access_token: Access token to access the remote Git repository
        """
        self.access_token = access_token
        self.logger = logging.getLogger('sqaaas_api.git')

    def setup_env(self, dirpath):
        """Setups the environment for handling remote repositories.

        :param dirpath: Directory to add the helper to
        """
        helper_path = os.path.join(dirpath, 'git-askpass-helper.sh')
        with open(helper_path, 'w') as f:
            f.writelines('%s\n' % l for l in ['#!/bin/sh', 'exec echo "$GIT_PASSWORD"'])
        os.chmod(helper_path, stat.S_IEXEC)
        os.environ['GIT_ASKPASS'] = helper_path
        os.environ['GIT_PASSWORD'] = self.access_token
        self.logger.debug('Git environment set: askpass helper & env vars')

    def clone_and_push(self, source_repo, target_repo, source_repo_branch=None):
        """Copies the source Git repository into the target one.

        Returns a tuple with the repository URL and default branch name.

        :param source_repo: Absolute URL of the source repository (e.g. https://example.org)
        :param target_repo: Absolute URL of the target repository (e.g. https://github.com/org/example)
        :param source_repo_branch: Specific branch name to use from the source repository
        """
        with tempfile.TemporaryDirectory() as dirpath:
            repo = None
            if source_repo_branch:
                repo = Repo.clone_from(source_repo, dirpath, single_branch=True, b=source_repo_branch)
            else:
                repo = Repo.clone_from(source_repo, dirpath)
            self.setup_env(dirpath)

            sqaaas = repo.create_remote(REMOTE_NAME, url=target_repo)
            try:
                sqaaas.fetch()
                sqaaas.pull()
                self.logger.debug('Repository updated: %s' % repo.remotes.sqaaas.url)
            except GitCommandError as e:
                self.logger.warning('Could not fetch&pull from target repository: %s (git msg: %s)' % (target_repo, e))
            finally:
                sqaaas.push()
                self.logger.debug('Repository pushed to remote: %s' % repo.remotes.sqaaas.url)
            default_branch = repo.active_branch
        return sqaaas.url, default_branch
