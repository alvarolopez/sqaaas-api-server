import logging
import requests
import time

from urllib.parse import urljoin

import jenkins


class JenkinsUtils(object):
    """Class for handling requests to Jenkins API.

    Support only for token-based access.
    """
    def __init__(self, endpoint, access_user, access_token):
        """JenkinsUtils object definition.

        :param endpoint: Jenkins endpoint URL
        :param access_user: Jenkins's access user
        :param access_token: Jenkins's access token
        """
        self.endpoint = endpoint
        self.access_user = access_user
        self.access_token = access_token
        self.server = jenkins.Jenkins(
            self.endpoint,
            username = self.access_user,
            password = self.access_token)
        self.logger = logging.getLogger('sqaaas_api.jenkins')

    def scan_organization(self, org_name='eosc-synergy-org'):
        path = '/job/%s/build?delay=0' % org_name
        r = requests.post(
            urljoin(self.endpoint, path),
            auth=(self.access_user, self.access_token))
        r.raise_for_status()
        self.logger.debug('Triggered GitHub organization scan')

    def get_job_info(self, name, depth=0):
        job_info = self.server.get_job_info(name, depth=depth)
        if job_info:
            self.logger.debug('Information job <%s> obtained from Jenkins' % name)
        else:
            self.logger.error('No info could be fetched for Jenkins job <%s>' % name)
        return job_info

    def get_job_url(self, job_name, org_name='eosc-synergy-org'):
        job_info = self.get_job_info(org_name)
        jobs = job_info['jobs']
        return [j['url'] for j in jobs if j['name'] == job_name]

    def build_job(self, job_name, branch_name, org_name='eosc-synergy-org'):
        full_job_name = '/'.join([org_name, job_name, branch_name])
        item_no = self.server.build_job(full_job_name)
        self.logger.debug('Triggered job build (item number: %s)' % item_no)
        queue_data = {}
        sleep_time_seconds = 15
        while 'executable' not in list(queue_data):
            self.logger.debug('Waiting for job to start (sleeping %s seconds)..' % sleep_time_seconds)
            time.sleep(sleep_time_seconds)
            queue_data = self.server.get_queue_item(item_no)

        return queue_data['executable']
