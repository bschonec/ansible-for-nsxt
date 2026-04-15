#!/usr/bin/python
# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, print_function
__metaclass__ = type

ANSIBLE_METADATA = {'metadata_version': '1.1',
                    'status': ['preview'],
                    'supported_by': 'community'}

DOCUMENTATION = '''
---
module: nsxt_group
short_description: Manage NSX-T Inventory Groups
description: 
    - Creates, updates, or deletes NSX-T Groups (Domain-level).
    - Supports idempotency and check_mode.
version_added: "2.7"
author: Brian Schonecker (Refactored)
options:
    hostname:
        description: Deployed NSX manager hostname.
        required: true
        type: str
    username:
        description: The username to authenticate with the NSX manager.
        required: true
        type: str
    password:
        description: The password to authenticate with the NSX manager.
        required: true
        type: str
        no_log: true
    state:
        description: The state of the group.
        choices: ['present', 'absent']
        required: true
        type: str
    name:
        description: The ID/Name of the group.
        required: true 
        type: str
    display_name:
        description: The display name of the group. Defaults to name if not set.
        type: str
    description:
        description: The description of the group.
        type: str
    domain:
        description: The domain to search for the groups.
        type: str
        default: default
    validate_certs:
        description: Validate SSL certificates.
        type: bool
        default: true
'''

import json
from ansible.module_utils.basic import AnsibleModule
from ansible_collections.vmware.ansible_for_nsxt.plugins.module_utils.vmware_nsxt import vmware_argument_spec, request
from ansible.module_utils._text import to_native

class NSXTGroupManager:
    def __init__(self, module):
        self.module = module
        self.params = module.params
        self.base_url = 'https://{}/policy/api/v1'.format(self.params['hostname'])
        self.group_path = '/infra/domains/{}/groups/{}'.format(self.params['domain'], self.params['name'])
        
        self.headers = {
            "Accept": "application/json",
            "Content-Type": "application/json"
        }

    def get_group(self):
        """Fetch current state of the group."""
        try:
            rc, resp = request(
                self.base_url + self.group_path,
                headers=self.headers,
                url_username=self.params['username'],
                url_password=self.params['password'],
                validate_certs=self.params['validate_certs'],
                ignore_errors=True
            )
            # NSX-T returns 404 if not found; request helper usually returns None or empty for 404
            return resp if rc == 200 else None
        except Exception:
            return None

    def update_group(self, method='PATCH', payload=None):
        """Execute the API call to create/update/delete."""
        if self.module.check_mode:
            return True

        try:
            rc, resp = request(
                self.base_url + self.group_path,
                data=json.dumps(payload) if payload else None,
                headers=self.headers,
                method=method,
                url_username=self.params['username'],
                url_password=self.params['password'],
                validate_certs=self.params['validate_certs'],
                ignore_errors=False
            )
            return True
        except Exception as err:
            self.module.fail_json(msg="API request failed: %s" % to_native(err))

    def run(self):
        state = self.params['state']
        current = self.get_group()
        
        # Determine Desired State
        desired = {
            'display_name': self.params.get('display_name') or self.params['name'],
            'description': self.params.get('description') or ''
        }

        changed = False
        message = ""

        if state == 'present':
            if not current:
                changed = True
                message = "Group created."
                self.update_group(method='PUT', payload=desired)
            else:
                # Compare only the fields we manage
                needs_update = any(current.get(k) != desired[k] for k in desired)
                if needs_update:
                    changed = True
                    message = "Group updated."
                    self.update_group(method='PATCH', payload=desired)
                else:
                    message = "Group already in desired state."

        elif state == 'absent':
            if current:
                changed = True
                message = "Group deleted."
                self.update_group(method='DELETE')
            else:
                message = "Group already absent."

        self.module.exit_json(changed=changed, message=message, name=self.params['name'])

def main():
    argument_spec = vmware_argument_spec()
    argument_spec.update(
        state=dict(required=True, choices=['present', 'absent']),
        domain=dict(type='str', default='default'),
        validate_certs=dict(type='bool', default=True),
        name=dict(required=True, type='str'),
        display_name=dict(type='str'),
        description=dict(type='str'),
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True
    )

    manager = NSXTGroupManager(module)
    manager.run()

if __name__ == '__main__':
    main()
