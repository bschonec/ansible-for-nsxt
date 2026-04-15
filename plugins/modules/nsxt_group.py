#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Copyright 2018 VMware, Inc.
# SPDX-License-Identifier: BSD-2-Clause OR GPL-3.0-only
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING,
# BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED.
# IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY,
# WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE,
# EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from __future__ import absolute_import, division, print_function
__metaclass__ = type


ANSIBLE_METADATA = {'metadata_version': '1.0',
                    'status': ['preview'],
                    'supported_by': 'community'}

DOCUMENTATION = '''
---
module: nsxt_group
short_description: List groups
description: Returns information about the configured group profiles.

version_added: "2.7"
author: Brian Schonecker
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
    state:
        description: The state of the group.
        required: true
        type: str
    description:
        description: The description of the group.
        required: false
        type: str
    name:
        description: The name of the group.
        required: true 
        type: str
    display_name:
        description: The display name of the group.
        required: false
        type: str
    domain:
        description: The domain to search for the groups.
        required: false
        type: str
        default: default

'''

EXAMPLES = '''
- name: List Group Profiles
  nsxt_group:
      hostname: "10.192.167.137"
      username: "admin"
      password: "Admin!23Admin"
      name: "my_group"
      display_name: "human-friendly-name"
      description: "Group for network devices"
      state: present
      domain: "my_domain"
      validate_certs: False
'''

RETURN = '''# '''

import json, time
from ansible.module_utils.basic import AnsibleModule
from ansible_collections.vmware.ansible_for_nsxt.plugins.module_utils.vmware_nsxt import vmware_argument_spec, request
from ansible.module_utils._text import to_native

def get_current_state(module, manager_url, mgr_username, mgr_password, validate_certs, domain, name):
  '''
  result: returns the group object with the display name provided
  '''

  try:
    (rc, resp) = request(manager_url+ '/infra/domains/' + domain + '/groups/' + name, headers=dict(Accept='application/json'),
                 url_username=mgr_username, url_password=mgr_password, validate_certs=validate_certs, ignore_errors=True)
  except Exception as err:
    # No group found.
    return None

  return resp

def normalize(obj):
  if not obj:
        return {}
  return {
    "display_name": obj.get("display_name"),
    "description": obj.get("description"),
  }

def main():
  argument_spec = vmware_argument_spec()
  argument_spec.update(
      dict(
          state=dict(required=True, choices=['present', 'absent']),
          domain=dict(type='str', default='default'),
          validate_certs=dict(type='bool', required=False, default=True),
          name=dict(required=True, type='str'),
          display_name=dict(required=False, type='str'),
          description=dict(required=False, type='str'),
      )
  )

  result = dict(
      changed=False,
      original_message='',
      message=''
  )

  module = AnsibleModule(argument_spec=argument_spec, supports_check_mode=True)

  # if the user is working with this module in only check mode we do not
  # want to make any changes to the environment, just return the current
  # state with no modifications
  if module.check_mode:
      module.exit_json(**result)

  mgr_hostname = module.params['hostname']
  mgr_username = module.params['username']
  mgr_password = module.params['password']
  state = module.params['state']
  domain = module.params['domain']
  validate_certs = module.params['validate_certs']
  description = module.params['description']
  name = module.params['name']
  display_name = module.params.get('display_name') or module.params['name']

  manager_url = 'https://{}/policy/api/v1'.format(mgr_hostname)
  headers = dict(Accept="application/json")
  headers['Content-Type'] = 'application/json'

  # Check to see if the group already exists.  We don't care about its properties (yet).
  current_state = get_current_state(module, manager_url, mgr_username, mgr_password, validate_certs, domain, name)

  # What is the desired state from the Ansible task?
  if state == 'present':

    # This is the dict that we create to compare what the current state is vs. the desired state.
    desired_state = {
      'display_name': display_name,
      'description': description,
    }

    payload = json.dumps(desired_state)

    # Does the group already exist?  If not, then there's no need to create it.  BUT, we must
    # check existing group parameters for any settings that need changing.
    if current_state:

      # The group already exists.  Now we have to check to see if we need to update any parameters.
      # Is what already exists different than what we want?
      changed = normalize(current_state) != normalize(desired_state)

      if changed:
        # The group already exists but we need to update its properties.
        try:
          (rc, resp) = request(manager_url+ '/infra/domains/' + domain + '/groups/' + name, data=payload, headers=headers, method='PATCH',
                                  url_username=mgr_username, url_password=mgr_password, validate_certs=validate_certs, ignore_errors=True)
          module.exit_json(changed=True, message="Group already exists but needed updating.")

        except Exception as err:
          module.fail_json(msg="Failed to add group.\n Error: [%s].\n Request_body[%s]." % (to_native(err), payload))

      else:
        # Group already exists and is in the desired state.
        module.exit_json(changed=False, message="Group already correct")

    else:

      # Group not yet created    
      try:
        (rc, resp) = request(manager_url+ '/infra/domains/' + domain + '/groups/' + name, data=payload, headers=headers, method='PUT',
                                url_username=mgr_username, url_password=mgr_password, validate_certs=validate_certs, ignore_errors=True)
        module.exit_json(changed=True, message="Group created.")

      except Exception as err:
        module.fail_json(msg="Failed to create group.\n Error: [%s].\n Request_body[%s]." % (to_native(err), payload))

  elif state == 'absent': 

    # Delete the group
    # Does the group already exist?  If not, then there's no need to delete it.
    if not current_state:
      module.exit_json(changed=False, message="Group didn't already exist")

    try:
      (rc, resp) = request(manager_url+ '/infra/domains/' + domain + '/groups/' + name, headers=headers, method='DELETE',
                              url_username=mgr_username, url_password=mgr_password, validate_certs=validate_certs, ignore_errors=True)
      module.exit_json(changed=True, message="Group deleted.")

    except Exception as err:
      module.fail_json(msg="Failed to delete group with display name \'%s\'. Error[%s]." % (name, to_native(err)))

if __name__ == '__main__':
	main()
