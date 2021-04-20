import logging

from gitlab import Gitlab


class GitlabUtils(object):
    """Class for handling requests to Gitlab API.

    Support only for token-based access.
    """
    def __init__(self, access_token):
        """GitlabUtils object definition.

        :param access_token: Gitlab's private token
        """
        self.client = Gitlab(
            'https://gitlab.com',
            private_token=access_token)
        self.logger = logging.getLogger('sqaaas_api.gitlab')

    def create_merge_request(self, upstream_repo_name, repo_name, branch, upstream_branch='master'):
        """Creates a merge request in the given upstream repository.

        :param upstream_repo_name:
        :param repo_name:
        :param branch:
        :param upstream_branch:
        """
        mrs = gl.mergerequests.list()

        # repo = self.client.get_repo(upstream_repo_name)
        # body = '''
        # Add JePL folder structure via SQAaaS.

        # FILES
        #   - [x] .sqa/config.yml
        #   - [x] .sqa/docker-compose.yml
        #   - [x] Jenkinsfile
        # '''
        # _repo_org = repo_name.split('/')[0]
        # head = ':'.join([_repo_org, branch])
        # self.logger.debug('Creating pull request: %s (head) -> %s (base)' % (head, upstream_branch))
        # pr = repo.create_pull(
        #     title='Set up JePL in project <%s>' % upstream_repo_name,
        #     body=body,
        #     head=head,
        #     base=upstream_branch)
        # self.logger.debug('Pull request successfully created: %s (head) -> %s (base)' % (head, upstream_branch))
        # return pr.raw_data
