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
      display_name: "my_group"
      state: present
      domain: "my_domain"
      validate_certs: False
'''

RETURN = '''# '''

import json, time
from ansible.module_utils.basic import AnsibleModule
from ansible_collections.vmware.ansible_for_nsxt.plugins.module_utils.vmware_nsxt import vmware_argument_spec, request
from ansible.module_utils._text import to_native

def get_groups(module, manager_url, mgr_username, mgr_password, validate_certs, domain, display_name):
  try:
    (rc, resp) = request(manager_url+ '/infra/domains/' + domain + '/groups', headers=dict(Accept='application/json'),
                      url_username=mgr_username, url_password=mgr_password, validate_certs=validate_certs, ignore_errors=True)
  except Exception as err:
    module.fail_json(msg='Error accessing groups for domain ' + domain + '. Error [%s]' % (to_native(err)))
  return resp

def get_group_with_display_name(module, manager_url, mgr_username, mgr_password, validate_certs, domain, display_name):
  '''
  result: returns the group object with the display name provided
  '''
  certificates = get_groups(module, manager_url, mgr_username, mgr_password, validate_certs, domain, display_name)
  for certificate in certificates['results']:
     if certificate.__contains__('display_name') and certificate['display_name'] == display_name:
        return certificate
  return None

def main():
  argument_spec = vmware_argument_spec()
  argument_spec.update(
      dict(
          state=dict(required=True, choices=['present', 'absent']),
          domain=dict(type='str', default='default'),
          validate_certs=dict(type='bool', required=False, default=True),
          description=dict(required=False, type='str'),
          display_name=dict(required=False, type='str'),
      )
  )

  module = AnsibleModule(argument_spec=argument_spec, supports_check_mode=True)

  mgr_hostname = module.params['hostname']
  mgr_username = module.params['username']
  mgr_password = module.params['password']
  state = module.params['state']
  domain = module.params['domain']
  validate_certs = module.params['validate_certs']
  description = module.params['description']
  display_name = module.params['display_name']

  manager_url = 'https://{}/policy/api/v1'.format(mgr_hostname)

  group_with_display_name = get_group_with_display_name(module, manager_url, mgr_username, mgr_password, validate_certs, domain, display_name)
# POST - create if doesn't exist
# PATCH - update existing or create if doesn't exist
# DELETE - captain obvious

  if state == 'present':

    # Does the group already exist?  If not, then there's no need to create it.
    if group_with_display_name:
      module.exit_json(changed=False, message="Group already exists. Response: [%s]" % str(group_with_display_name))

    # The NSX API will allow us to use the PATCH method to both create and modify the group.
    payload = json.dumps({
      'description': description,
      'display_name': display_name,
    })

    try:
      headers = dict(Accept="application/json")
      headers['Content-Type'] = 'application/json'
      (rc, resp) = request(manager_url+ '/infra/domains/' + domain + '/groups/' + display_name, data=payload, headers=headers, method='PATCH',
                              url_username=mgr_username, url_password=mgr_password, validate_certs=validate_certs, ignore_errors=True)
    except Exception as err:
      module.fail_json(msg="Failed to add group.\n Error: [%s].\n Request_body[%s]." % (to_native(err), payload))

    module.exit_json(changed=True, result=resp, message="Group created. Response: [%s]" % str(resp))

  elif state == 'absent': 
    # Delete the group
    # Does the group already exist?  If not, then there's no need to delete it.
    if not group_with_display_name:
      module.fail_json(msg="Group with display name \'%s\' doesn't exists." % display_name)
    group_id = group_with_display_name['id']
    try:
      (rc, resp) = request(manager_url+ '/infra/domains/' + domain + '/groups/' + display_name, data=payload, headers=headers, method='DELETE',
                              url_username=mgr_username, url_password=mgr_password, validate_certs=validate_certs, ignore_errors=True)
    except Exception as err:
      module.fail_json(msg="Failed to delete group with display name \'%s\'. Error[%s]." % (display_name, to_native(err)))

    module.exit_json(changed=True, object_name=certificate_id, message="Certificate with certificate id: %s deleted." % certificate_id)



if __name__ == '__main__':
	main()
