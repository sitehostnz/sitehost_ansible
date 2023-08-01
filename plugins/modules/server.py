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
  - "SiteHost Developers (developers@sitehost.co.nz)"
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

from collections import OrderedDict  # noqa: E402

from ansible.module_utils.basic import AnsibleModule  # noqa: E402

from ..module_utils.sitehost import SitehostAPI  # noqa: E402


class AnsibleSitehostServer:
    def __init__(self, module, api):
        self.sh_api = api
        self.module = module
        self.result = {
            "changed": False,
            "sitehost_server": dict(),
            "diff": dict(before=dict(), after=dict()),
            "sitehost_api": {
                "api_endpoint": self.module.params["api_endpoint"],
            },
        }

    def absent(self):
        """deletes a server"""
        server_to_delete = self.get_server_by_name()

        if not server_to_delete:  # server does not exist, so just skip and continue
            self.result["skipped"] = True
            self.module.exit_json(
                msg="Server does not exist, skipping task.", **self.result
            )

        #  check mode
        if self.module.check_mode:
            self.module.exit_json(changed=True)

        body = OrderedDict()
        body["name"] = server_to_delete["name"]
        deleteresult = self.sh_api.api_query(
            path="/server/delete.json",
            method="POST",
            data=body,
        )

        # pause execution until the server is fully deleted
        delete_job_result = self.sh_api.wait_for_job(
            job_id=deleteresult["return"]["job_id"]
        )

        self.result["changed"] = True

        self.result["diff"]["before"] = server_to_delete
        self.result["diff"]["after"] = delete_job_result
        self.result["message"] = delete_job_result["message"]

        self.module.exit_json(**self.result)

    def handle_power_status(self):
        """this handles starting, stopping, and restarting servers"""
        # check if the server exist
        if not self.get_server_by_name():
            #  check mode, server might not be created yet
            if self.module.check_mode:
                self.module.exit_json(changed=True)
            self.module.fail_json(msg="ERROR: server does not exist.")

        requested_server_state = self.module.params.get("state")

        # always restart server when requested
        if requested_server_state == "restarted":

            #  check mode
            if self.module.check_mode:
                self.module.exit_json(changed=True)

            body = OrderedDict()
            body["name"] = self.module.params.get("name")
            body["state"] = "reboot"

            restart_result = self.sh_api.api_query(
                path="/server/change_state.json", method="POST", data=body
            )

            restart_job = self.sh_api.wait_for_job(
                job_id=restart_result["return"]["job_id"]
            )
            self.module.exit_json(changed=True, job_status=restart_job)

        current_server_state = self.sh_api.api_query(
            path="/server/get_state.json",
            query_params={"name": self.module.params.get("name")},
        )["return"]["state"]

        server_state_map = {
            "On": "started",
            "Off": "stopped",
        }

        # if server is the requested state already, skip task
        if server_state_map[current_server_state] == requested_server_state:
            self.module.exit_json(
                skipped=True,
                msg=f"server already {server_state_map[current_server_state]}, skipped task",
                **self.result,
            )

        #  check mode
        if self.module.check_mode:
            self.module.exit_json(changed=True)

        # the server state is different from requested state, start/stop server
        body = OrderedDict()
        body["name"] = self.module.params.get("name")
        body["state"] = (
            "power_on" if requested_server_state == "started" else "power_off"
        )

        startjob = self.sh_api.api_query(
            path="/server/change_state.json", method="POST", data=body
        )
        startresult = self.sh_api.wait_for_job(job_id=startjob["return"]["job_id"])

        self.module.exit_json(changed=True, job_status=startresult)

    def create(self):
        """provisions a new server"""

        #  check mode
        if self.module.check_mode:
            self.module.exit_json(changed=True)

        body = OrderedDict()

        body["label"] = self.module.params["label"]
        body["location"] = self.module.params["location"]
        body["product_code"] = self.module.params["product_code"]
        body["image"] = self.module.params["image"]
        body["params[ipv4]"] = "auto"

        self.result["changed"] = True

        self.result["diff"]["before"] = dict()
        self.result["diff"]["after"] = body

        

        resource = self.sh_api.api_query(
            path="/server/provision.json",
            method="POST",
            data=body,
        )

        self.result["sitehost_server"]=resource
        
        if resource:
            self.sh_api.wait_for_job(
                job_id=resource["return"]["job_id"], state="Completed"
            )

        self.module.exit_json(**self.result)

    def upgrade(self):
        """
        upgrades the server, called when server name is provided and server exists
        It will first stage the upgrade then commit the upgrade with the api, restarts server
        """
        server_to_upgrade = self.get_server_by_name()
        # check if the server exist
        if not server_to_upgrade:
            #  check mode, the server may had been created earlier
            if self.module.check_mode:
                self.module.exit_json(changed=True)
            self.module.fail_json(msg="ERROR: Server does not exist.")

        # check if server plan is same as inputed product code
        if server_to_upgrade["product_code"] == self.module.params["product_code"]:
            self.module.exit_json(
                skipped=True,
                msg="Requested product is the same as current server product, skipping.",
            )

        #  check mode
        if self.module.check_mode:
            self.module.exit_json(changed=True)

        # stage server upgrade
        body = OrderedDict()
        body["name"] = self.module.params.get("name")
        body["plan"] = self.module.params.get("product_code")
        self.sh_api.api_query(
            path="/server/upgrade_plan.json", method="POST", data=body
        )

        # commit upgrade, will restart server
        body = OrderedDict()
        body["name"] = self.module.params.get("name")
        upgrade_job = self.sh_api.api_query(
            path="/server/commit_disk_changes.json", method="POST", data=body
        )

        job_result = self.sh_api.wait_for_job(upgrade_job["return"]["job_id"])

        server_after_upgrade = self.get_server_by_name()

        self.result["diff"]["before"] = server_to_upgrade
        self.result["diff"]["after"] = server_after_upgrade
        self.result["job_result"] = job_result
        self.result["msg"] = job_result["message"]
        self.result["changed"] = True

        self.module.exit_json(**self.result)

    def create_or_upgrade(self):
        if self.module.params.get("name"):  # if server name exist, upgrade the server
            self.upgrade()
        elif self.module.params.get(
            "label"
        ):  # else if label only, create the new server
            self.create()
        else:  # something is wrong with the code
            self.module.fail_json(msg="ERROR: no name or label given, exiting")

    def get_server_by_name(self, server_name=None):
        """return a server by its server name"""
        if server_name is None:
            server_name = self.module.params.get("name")

        retrieved_server = self.sh_api.api_query(
            path="/server/get_server.json",
            query_params=OrderedDict({"name": server_name}),
        )

        # if server exist, return it
        if retrieved_server["status"]:
            return retrieved_server["return"]

        return None #  server does not exist


def main():
    argument_spec = SitehostAPI.sitehost_argument_spec()
    argument_spec.update(
        dict(
            label=dict(type="str"),
            name=dict(type="str"),
            location=dict(type="str"),
            product_code=dict(type="str"),
            image=dict(type="str"),
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
            notes=dict(type="str"),
        )  # type: ignore
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        required_if=(("state", "present", ("product_code",)),),
        supports_check_mode=True,
    )

    sitehost_api = SitehostAPI(
        module=module,
        api_key=module.params["api_key"],
        api_client_id=module.params["api_client_id"],
    )

    sitehostserver = AnsibleSitehostServer(module=module, api=sitehost_api)

    state = module.params["state"]  # type: ignore

    if state == "absent":
        sitehostserver.absent()
    elif state == "present":
        sitehostserver.create_or_upgrade()
    else:
        sitehostserver.handle_power_status()


if __name__ == "__main__":
    main()
