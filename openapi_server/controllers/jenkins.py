import logging
import requests
import time

from urllib.parse import urljoin
from urllib.parse import quote_plus

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

    @staticmethod
    def format_job_name(job_name):
        """Format job name according to what is expected by Jenkins.

        Slash symbol '/' is double-encoded: ''%252F' instead of '%2F'

        :param job_name: Name of the Jenkins job
        """
        return quote_plus(job_name.replace('/', '%2F'))

    def scan_organization(self, org_name='eosc-synergy-org'):
        path = '/job/%s/build?delay=0' % org_name
        r = requests.post(
            urljoin(self.endpoint, path),
            auth=(self.access_user, self.access_token))
        r.raise_for_status()
        self.logger.debug('Triggered GitHub organization scan')

    def get_job_info(self, name, depth=0):
        job_info = {}
        try:
            job_info = self.server.get_job_info(name, depth=depth)
            self.logger.debug('Information job <%s> obtained from Jenkins' % name)
        except jenkins.JenkinsException:
            self.logger.error('No info could be fetched for Jenkins job <%s>' % name)
        return job_info

    def exist_job(self, job_name):
        """Check whether given job is defined in Jenkins.

        :param job_name: job name including folder/s, name & branch
        """
        return self.get_job_info(job_name)

    def build_job(self, full_job_name):
        """Build existing job.

        :param full_job_name: job name including folder/s, name & branch
        """
        item_no = self.server.build_job(full_job_name)
        self.logger.debug('Triggered job build (queue item number: %s)' % item_no)
        return item_no

    def get_queue_item(self, item_no):
        """Get the status of the build item in the Jenkins queue.

        :param item_no: item number in the Jenkins queue.
        """
        queue_data = self.server.get_queue_item(item_no)
        executable_data = None
        if 'executable' not in list(queue_data):
            self.logger.debug('Waiting for job to start. Queue item: %s' % queue_data['url'])
        else:
            executable_data = queue_data['executable']
            self.logger.debug('Job started the execution (url: %s, number: %s)' % (
                executable_data['url'], executable_data['number']
            ))
        return executable_data

    def get_build_info(self, full_job_name, build_no, depth=0):
        self.logger.debug('Getting status for job <%s> (build_no: %s)' % (full_job_name, build_no))
        return self.server.get_build_info(full_job_name, build_no, depth=depth)['result']

    def delete_job(self, full_job_name):
        self.logger.debug('Deleting Jenkins job: %s' % full_job_name)
        self.server.delete_job(full_job_name)
        self.logger.debug('Jenkins job <%s> successfully deleted' % full_job_name)
