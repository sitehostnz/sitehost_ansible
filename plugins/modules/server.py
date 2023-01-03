#!/usr/bin/python
# -*- coding: utf-8 -*-
#

from __future__ import absolute_import, division, print_function

__metaclass__ = type


DOCUMENTATION = """
-----
module: server
short_description: Manage servers
description:
  - Manage servers
version_added: "0.1"
author:
  - "Gonzalo Rios (@gonzariosm)"
options:
  label:
    description:
      - Label for the new server..
    required: true
    type: str
  location:
    description:
      - The code for the location to provision the new server at.
    required: true
    type: str
  product_code:
    description:
      - The code for the product to use for the new server.
    required: true
    type: str
  image:
    description:
      - The image to use for the new server.
    required: true
    type: str
  ssh_keys:
    description:
      - List of SSH key names passed to the server on creation.
    type: list
    elements: str
  state:
    description:
      - State of the instance.
    default: present
    choices: [ present, absent, started, stopped, restarted ]
    type: str
extends_documentation_fragment:
  - sitehost.cloud.shpy
'''

EXAMPLES = '''
---
- name: Create a VPS with 1.5G RAM OS Ubuntu 20.04
  sitehost.cloud.server:
    label: webserver
    location: AKLCITY
    product_code: XENLIT
    image: ubuntu-focal.amd64
    ssh_keys:
      - my ssh key
'''

RETURN = '''
---
sitehost_api:
  description: Response from SiteHost API.
  returned: success
  type: dict
  contains:
    api_endpoint:
      description: Endpoint used for the API requests.
      returned: success
      type: str
      sample: "https://api.staging.sitehost.nz/1.2"
sitehost_instance:
  description: Response from SiteHost API.
  returned: success
  type: dict
  contains:
    return:
      description: Details of server provision.
      returned: success
      type: list
      contains:
        job_id:
          description: Job ID.
          returned: success
          type: str
          sample: 2251119
        name:
          description: Server name.
          returned: success
          type: str
          sample: "server-name"
        password:
          description: Password for root user.
          returned: success
          type: str
          sample: "4d6bxsnx"
        ips:
          description: List of IPs assigned.
          returned: success
          type: list
          sample: [ 192.168.11.108 ]
        server_id:
          description: Server ID.
          returned: success
          type: str
          sample: "11353"
"""

from collections import OrderedDict

from ansible.module_utils.basic import AnsibleModule

from ..module_utils.shpy import AnsibleSitehost, sitehost_argument_spec


class AnsibleSitehostServer(AnsibleSitehost):
    def get_ssh_key_ids(self):
        ssh_key_names = list(self.module.params["ssh_keys"])
        ssh_keys = self.query_list(path="/ssh-keys", result_key="ssh_keys")

        ssh_key_ids = list()
        for ssh_key in ssh_keys:
            if ssh_key["name"] in ssh_key_names:
                ssh_key_ids.append(ssh_key["id"])
                ssh_key_names.remove(ssh_key["name"])

        if ssh_key_names:
            self.module.fail_json(msg="SSH key names not found: %s" % ", ".join(ssh_key_names))

        return ssh_key_ids

    def transform_resource(self, resource):
        if not resource:
            return resource

        features = resource.get("features", list())
        resource["backups"] = "enabled" if "auto_backups" in features else "disabled"
        resource["enable_ipv6"] = "ipv6" in features
        resource["ddos_protection"] = "ddos_protection" in features
        resource["vpcs"] = self.get_instance_vpcs(resource=resource)

        return resource

    def configure(self):
        if self.module.params["state"] != "absent":
            if self.module.params["ssh_keys"] is not None:
                # sshkey_id ist a list of ids
                self.module.params["sshkey_id"] = self.get_ssh_key_ids()

    def handle_power_status(self, resource, state, action, power_status, force=False):
        if state == self.module.params["state"] and (resource["power_status"] != power_status or force):
            self.result["changed"] = True
            if not self.module.check_mode:
                self.api_query(
                    path="%s/%s/%s" % (self.resource_path, resource[self.resource_key_id], action),
                    method="POST",
                )
                resource = self.wait_for_state(resource=resource, key="power_status", state=power_status)
        return resource

    def create(self):
        #return super(AnsibleSitehostServer, self).create()
        # if state == self.module.params["state"] and (resource["power_status"] != power_status or force):
        #     self.result["changed"] = True
        #     if not self.module.check_mode:
        #         self.api_query(
        #             path="%s/%s/%s" % (self.resource_path, resource[self.resource_key_id], action),
        #             method="POST",
        #         )
        #         resource = self.wait_for_state(resource=resource, key="power_status", state=power_status)
        # return resource

        data = OrderedDict()

        for param in self.resource_create_param_keys:
            data[param] = self.module.params.get(param)

        self.result["changed"] = True
        resource = dict()

        self.result["diff"]["before"] = dict()
        self.result["diff"]["after"] = data

        if not self.module.check_mode:
            resource = self.api_query(
                path="%s/provision.json" % (self.resource_path),
                method="POST",
                data=data,
            )

        return resource.get(self.resource_result_key_singular) if resource else dict()

    def update(self, resource):
        user_data = self.get_user_data(resource=resource)
        resource["user_data"] = user_data.encode()

        if self.module.params["vpcs"] is not None:
            resource["attach_vpc"] = list()
            for vpc in list(resource["vpcs"]):
                resource["attach_vpc"].append(vpc["id"])

            # detach_vpc is a list of ids to be detached
            resource["detach_vpc"] = list()
            self.module.params["detach_vpc"] = self.get_detach_vpcs_ids(resource=resource)

        return super(AnsibleSitehostServer, self).update(resource=resource)

    def create_or_update(self):
        resource = super(AnsibleSitehostServer, self).create_or_update()
        if resource:
            resource = self.wait_for_state(resource=resource, key="status", state="active")
            resource = self.wait_for_state(resource=resource, key="server_status", state="locked", cmp="!=")
            # Hanlde power status
            resource = self.handle_power_status(resource=resource, state="stopped", action="halt", power_status="stopped")
            resource = self.handle_power_status(resource=resource, state="started", action="start", power_status="running")
            resource = self.handle_power_status(resource=resource, state="restarted", action="reboot", power_status="running", force=True)
        return resource

    def transform_result(self, resource):
        if resource:
            resource["user_data"] = self.get_user_data(resource=resource)
        return resource


def main():
    argument_spec = sitehost_argument_spec()
    argument_spec.update(
        dict(
            label=dict(type="str", required=True),
            location=dict(type="str", required=True),
            product_code=dict(type="str", required=True),
            image=dict(type="str", required=True),
            ssh_keys=dict(type="list", elements="str", no_log=False),
            state=dict(
                choices=[
                    "present",
                    "absent",
                    "started",
                    "stopped",
                    "restarted",
                ],
                default="present",
            ),
        )  # type: ignore
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        required_if=(("state", "present", ("product_code",)),),
        supports_check_mode=True,
    )

    sitehost = AnsibleSitehostServer(
        module=module,
        namespace="sitehost_server",
        resource_path="/server",
        resource_result_key_singular="server",
        resource_create_param_keys=[
            "label",
            "location",
            "product_code",
            "image",
            "ssh_keys",
        ],
        resource_update_param_keys=[
            "product_code",
        ],
        resource_key_name="label",
    )

    state = module.params.get("state")  # type: ignore
    if state == "absent":
        sitehost.absent()
    else:
        sitehost.present()


if __name__ == "__main__":
    main()
