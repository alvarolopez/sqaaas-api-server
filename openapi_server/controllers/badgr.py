import json
import logging
import requests

from urllib.parse import urljoin


SW_CRITERIA_MAP = {
    'qc_style': 'https://indigo-dc.github.io/sqa-baseline/#code-style-qc.sty',
    'qc_unit': 'https://indigo-dc.github.io/sqa-baseline/#unit-testing-qc.uni',
    'qc_functional': 'https://indigo-dc.github.io/sqa-baseline/#functional-testing-qc.fun',
    'qc_doc': 'https://indigo-dc.github.io/sqa-baseline/#documentation-qc.doc',
    'qc_security': 'https://indigo-dc.github.io/sqa-baseline/#security-qc.sec'
}
SRV_CRITERIA_MAP = {
}


class BadgrUtils(object):
    """Class for handling requests to Badgr API."""
    def __init__(self, endpoint, access_user, access_pass, issuer_name, badgeclass_name):
        """BadgrUtils object definition.

        :param endpoint: Badgr endpoint URL
        :param access_user: Badgr's access user id
        :param access_pass: Badgr's user password
        :param issuer_name: String that corresponds to the Issuer name (as it appears in Badgr web)
        :param badgeclass_name: String that corresponds to the BadgeClass name (as it appears in Badgr web)
        """
        self.logger = logging.getLogger('sqaaas_api.badgr')
        self.endpoint = endpoint
        self.issuer_name = issuer_name
        self.badgeclass_name = badgeclass_name
        self.access_token = self.get_token(
            access_user,
            access_pass
        )

    def get_token(self, access_user, access_pass):
        """Obtains a Bearer-type token according to the provided credentials.

        :param access_user: User ID
        :param access_pass: User password
        """
        path = 'o/token'
        self.logger.debug('Getting user token from Badgr API: \'GET %s\'' % path)
        r = requests.post(
            urljoin(self.endpoint, path),
            data = {
                'username': access_user,
                'password': access_pass
            }
        )
        self.logger.debug('\'GET %s\' response content: %s' % (path, r.__dict__))
        r.raise_for_status()
        r_json = r.json()
        return r_json['access_token']

    def get_issuers(self):
        """Gets all the Issuers associated with the current user."""
        path = 'v2/issuers'
        headers = {
            'Authorization': 'Bearer %s' % self.access_token
        }
        self.logger.debug('Getting issuers from Badgr API: \'GET %s\'' % path)
        r = requests.get(
            urljoin(self.endpoint, path),
            headers=headers
        )
        self.logger.debug('\'GET %s\' response content: %s' % (path, r.__dict__))
        if r.ok:
            r_json = r.json()
            return r_json['result']

    def get_badgeclasses(self, issuer_id):
        """Gets all the BadgeClasses associated with the given Issuer.

        :param issuer_id: entityID of the issuer where this BadgeClass belongs to.
        """
        path = 'v2/issuers/%s/badgeclasses' % issuer_id
        headers = {
            'Authorization': 'Bearer %s' % self.access_token
        }
        self.logger.debug('Getting BadgeClasses for Issuer <%s> from Badgr API: \'GET %s\'' % (issuer_id, path))
        r = requests.get(
            urljoin(self.endpoint, path),
            headers=headers
        )
        self.logger.debug('\'GET %s\' response content: %s' % (path, r.__dict__))
        if r.ok:
            r_json = r.json()
            return r_json['result']

    def _get_matching_entity_id(self, entity_name, entity_type, **kwargs):
        """Get the ID of the specified entity type that matches the given name.

        :param entity_name: String that designates the entity (as it appears in Badgr web)
        :param entity_type: valid types are ('issuer', 'badgeclass')
        """
        if entity_type == 'issuer':
            all_entities = self.get_issuers()
        elif entity_type == 'badgeclass':
            all_entities = self.get_badgeclasses(**kwargs)

        entity_name_dict = dict([
            [entity['name'], entity['entityId']]
                for entity in all_entities
                    if entity['name'] == entity_name
        ])
        entity_name_list = entity_name_dict.keys()
        if len(entity_name_list) > 1:
            self.logger.warn('Number of matching entities (type: %s) bigger than one: %s' % (entity_type, entity_name_list))
            raise Exception('Found more than one entity (type: %s) matching the given name' % entity_type)
        if len(entity_name_list) == 0:
            self.logger.warn('Found 0 matches for entity name <%s> (type: %s)' % (entity_name, entity_type))
            raise Exception('No matching entity name found (type: %s)' % entity_type)

        return entity_name_dict[entity_name]

    def get_badgeclass_entity(self):
        """Returns the BadgeClass entityID corresponding to the given Issuer and Badgeclass name combination."""
        issuer_id = self._get_matching_entity_id(
            self.issuer_name,
            entity_type='issuer'
        )
        badgeclass_id = self._get_matching_entity_id(
            self.badgeclass_name,
            entity_type='badgeclass',
            issuer_id=issuer_id
        )
        return badgeclass_id

    def issue_badge(self, commit_id, commit_url, ci_build_url, sw_criteria=[], srv_criteria=[]):
        """Issues a badge (Badgr's assertion).

        :param commit_id: Commit ID assigned by git as a result of pushing the JePL files.
        :param commit_url: Absolute URL pointing to the commit that triggered the pipeline
        :param ci_build_url: Absolute URL pointing to the build results of the pipeline
        :param sw_criteria: List of fulfilled criteria codes from the Software baseline
        :param srv_criteria: List of fulfilled criteria codes from the Service baseline
        """
        badgeclass_id = self.get_badgeclass_entity()
        self.logger.info('BadgeClass entityId found for Issuer <%s> and BadgeClass <%s>: %s' % (
            self.issuer_name,
            self.badgeclass_name,
            badgeclass_id
        ))
        path = 'v2/badgeclasses/%s/assertions' % badgeclass_id
        headers = {
            'Authorization': 'Bearer %s' % self.access_token,
            'Content-Type': 'application/json'
        }
        # Assertion data
        narrative = {
            'Software': '\n'.join([
                '- [%s](%s)\n' % (criterion, SW_CRITERIA_MAP[criterion])
                    for criterion in sw_criteria]),
            'Service': '\n'.join([
                '- [%s](%s)\n' % (criterion, SRV_CRITERIA_MAP[criterion])
                    for criterion in srv_criteria])
        }
        assertion_data = json.dumps({
            'recipient': {
              'identity': commit_url,
              'hashed': True,
              'type': 'url'
            },
            'narrative': '\n\n'.join([
                '\n'.join(['Source code change (SHA: [%s](%s)) have passed successfully the ' % (commit_id, commit_url),
                           'validation of the following %s QA criteria:' % criteria_type, criteria_msg])
                    for criteria_type, criteria_msg in narrative.items() if criteria_msg
            ]),
            'evidence': [
              {
                'url': ci_build_url,
                'narrative': 'Build page from Jenkins CI'
              }
            ]
        })
        self.logger.debug('Assertion data: %s' % assertion_data)

        self.logger.debug('Posting to get an Assertion of BadgeClass <%s> from Badgr API: \'POST %s\'' % (self.badgeclass_name, path))
        r = requests.post(
            urljoin(self.endpoint, path),
            headers=headers,
            data=assertion_data
        )
        r_json = r.json()
        self.logger.debug('Result from \'POST %s\': %s' % (path, r_json))

        if r.ok:
            if len(r_json['result']) > 1:
                self.logger.warn('More than one badge being issued')

            # Return the first result
            return r_json['result'][0]
        else:
            if 'fieldErrors' in r_json.keys() and r_json['fieldErrors']:
                self.logger.warn('Unsuccessful POST (Field errors): %s' % r_json['fieldErrors'])
            if 'validationErrors' in r_json.keys() and r_json['validationErrors']:
                self.logger.warn('Unsuccessful POST (Validation errors): %s' % r_json['validationErrors'])
            r.raise_for_status()
