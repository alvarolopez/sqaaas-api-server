import logging
import requests

from urllib.parse import urljoin


class BadgrUtils(object):
    """Class for handling requests to Badgr API."""
    def __init__(self, endpoint, access_user, access_pass, entity):
        """BadgrUtils object definition.

        :param endpoint: Badgr endpoint URL
        :param access_user: Badgr's access user id
        :param access_pass: Badgr's user password
        :param entity: Issuer's BadgeClass entity id
        """
        self.endpoint = endpoint
        self.access_token = self.get_token(
            access_user,
            access_pass
        )
        self.entity = entity
        self.logger = logging.getLogger('sqaaas_api.badgr')

    def get_token(self, access_user, access_pass):
        """Obtains a Bearer-type token according to the provided credentials.

        :param access_user: User ID
        :param access_pass: User password
        """
        path = 'o/token'
        r = requests.post(
            urljoin(self.endpoint, path),
            data = {
                'username': access_user,
                'password': access_pass
            }
        )
        r.raise_for_status()
        r_json = r.json()
        self.access_token = r_json['access_token']

    def issue_badge(self, commit_url, ci_build_url, sw_criteria=[], srv_criteria=[]):
        """Issues a badge (Badgr's assertion).

        :param commit_url: Absolute URL pointing to the commit that triggered the pipeline
        :param ci_build_url: Absolute URL pointing to the build results of the pipeline
        :param sw_criteria: List of fulfilled criteria codes from the Software baseline
        :param srv_criteria: List of fulfilled criteria codes from the Service baseline
        """
        path = 'v2/badgeclasses/%s/assertions' % self.entity
        headers = {
            'Authorization': 'Bearer %s' % self.access_token,
            'Content-Type': 'application/json'
        }
        # Assertion data
        narrative = {
            'Software': '\n'.join([
                '- [%s](%s)\n' % (criterion, '')
                    for criterion in sw_criteria]),
            'Service': '\n'.join([
                '- [%s](%s)\n' % (criterion, '')
                    for criterion in srv_criteria])
        }
        assertion_data = {
            'recipient': {
              'identity': commit_url,
              'hashed': true,
              'type': 'url'
            },
            'narrative': '\n\n'.join([
                '\n'.join(['Successful validation of %s QA criteria:' % criteria_type, criteria_msg])
                    for criteria_type, criteria_msg in narrative.items() if criteria_msg
            ]),
            'evidence': [
              {
                'url': ci_build_url,
                'narrative': '\n'.join([
                    '- Version validated (commit): %s' % commit_url,
                    '- Build URL in the CI system: %s' % ci_build_url,
                ])
              }
            ]
        }
        r = requests.post(
            urljoin(self.endpoint, path),
            headers=headers,
            data=assertion_data
        )
        r.raise_for_status()
        r_json = r.json()
        return r_json
