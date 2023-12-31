#!/usr/bin/python
# -*- coding: utf-8 -*-
#

# Copyright: Contributors to the Ansible project
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type


CLOUD_CONTAINER_SERVER_PRODUCT_CODE = [
    "CLDCON1",
    "CLDCON2",
    "CLDCON4",
    "CLDCON6",
    "CLDCON8",
]
DAEMON_JOB_TYPE = "daemon"
SCHEDULER_JOB_TYPE = "scheduler"

DOCUMENTATION = """
---
module: server
short_description: Manage SiteHost servers
description: 
  - Used for provisioning, deleting, upgrading, starting and stopping servers on your SiteHost account.
author:
  - "SiteHost Developers (developers@sitehost.co.nz)"
options:
  state:
    description:
      - Indicates the desired state of the server.
      - C(present) will either upgrade or create a server; 'label' is required for provisioning a server, and use 'name' for upgrading a server.
      - C(absent) will delete the server.
      - C(started) for powering on the server.
      - C(stopped) for powering off the server.
      - C(restarted) for restarting the server.
    default: present
    choices: [ present, absent, started, stopped, restarted ]
    type: str
  label:
    description:
      - User chosen label of the new server, mutually exclusive to C(name).
      - Please ensure that verbose mode C(-v) is enabled to see the password of the newly created server.
    type: str
  name:
    description:
      - Unique auto generated machine name for server.
      - Used to select a server that is already present.
    type: str
  location:
    description:
      - The code for the L(location,https://kb.sitehost.nz/developers/api/locations) to provision the new server at. eg. AKLCITY
    type: str
  product_code:
    description:
      - The code for the L(server specification,https://kb.sitehost.nz/developers/api/product-codes) to use when provisioning the new server. eg. XENLIT
    type: str
  image:
    description:
      - The L(image,https://kb.sitehost.nz/developers/api/images) to use for the new server. eg. ubuntu-jammy-pvh.amd64
    type: str
  api_key:
    description: 
      - Your SiteHost api key L(generated from CP,https://kb.sitehost.nz/developers/api#creating-an-api-key).
    required: true
    type: str
  api_client_id:
    description:
      - The client id of your SiteHost account.
    required: true
    type: int
"""

EXAMPLES = """
# Creating a VPS, use `-v` as argument to see password
- name: Create a 1 core VPS with ubuntu jammy image
  sitehost.cloud.server:
    label: myserver
    location: AKLCITY
    product_code: XENLIT
    image: ubuntu-jammy-pvh.amd64
    api_client_id: "{{ CLIENT_ID }}"
    api_key: "{{ USER_API_KEY }}"
    state: present

# Create a VPS and register its output to shserver and outputs the password
- name: Create a 1 core VPS with ubuntu jammy image
  sitehost.cloud.server:
    label: myserver
    location: AKLCITY
    product_code: XENLIT
    image: ubuntu-jammy-pvh.amd64
    api_client_id: "{{ CLIENT_ID }}"
    api_key: "{{ USER_API_KEY }}"
    state: present
  register: shserver 

- name: output shserver
  ansible.builtin.debug:
    msg: "{{ shserver.server.password }}"

# Creating a server then upgrading it
- name: Create a 1 core VPS with ubuntu jammy image
  sitehost.cloud.server:
    label: myserver
    location: AKLCITY
    product_code: XENLIT
    image: ubuntu-jammy-pvh.amd64
    api_client_id: "{{ CLIENT_ID }}"
    api_key: "{{ USER_API_KEY }}"
    state: present
  register: shserver 

- name: upgrade the previously created server
    sitehost.cloud.server:
    name: "{{ shserver.server.name }}"
    product_code: XENPRO
    api_client_id: "{{ CLIENT_ID }}"
    api_key: "{{ USER_API_KEY }}"
    state: present

# Restarts the previously created server
- name: restart server
  sitehost.cloud.server:
    name: "{{ shserver.server.name }}"
    api_client_id: "{{ CLIENT_ID }}"
    api_key: "{{ USER_API_KEY }}"
    state: restarted

# Deletes server 
- name: delete server
  sitehost.cloud.server:
    name: "{{ shserver.server.name }}"
    api_client_id: "{{ CLIENT_ID }}"
    api_key: "{{ USER_API_KEY }}"
    state: absent

"""

RETURN = """
msg:
  description: Text that indicates the status of the module.
  returned: always
  type: str
  sample: webserver1 has been deleted
server: 
  description: The sitehost server being actioned. Note that there is more information output on server creation and upgrade.
  returned: success
  type: dict
  contains:
    label: 
      description: User chosen label for the server.
      returned: success
      type: str
      sample: mywebserver
    name:
      description: Unique system generated name for server.
      returned: success
      type: str
      sample: mywebserv2
    password:
      description: Password for the root user, only returned during server creation.
      returned: success
      type: str
      sample: Up8Da5oE60ns
    state:
      description: The state of the server after executing the command.
      return: success
      type: str
      sample: 
        - On
        - Off
        - Reboot
        - Deleted
"""


from collections import OrderedDict  # noqa: E402

from ansible.module_utils.basic import AnsibleModule  # noqa: E402

from ..module_utils.sitehost import SitehostAPI  # noqa: E402


class AnsibleSitehostServer:
    _SERVER_STATE_MAP = {"On": "started", "Off": "stopped"}
    # converts module user input to appropriate api call state
    _API_STATE_MAP = {
        "restarted": "reboot",
        "started": "power_on",
        "stopped": "power_off",
    }

    def __init__(self, module, api):
        self.sh_api = api
        self.module = module
        self.result = {
            "changed": False,
            "server": dict(),
        }

    def absent(self):
        """deletes a server"""
        server_to_delete = self._get_server_by_name()
        if not server_to_delete:  # server does not exist, so just continue
            self.module.exit_json(msg="Server does not exist", **self.result)

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

        self.sh_api.wait_for_job(job_id=deleteresult["return"]["job_id"])

        self.result["changed"] = True
        self.result["msg"] = f"{server_to_delete['name']} has been deleted"
        self.result["server"] = {
            "label": server_to_delete["label"],
            "name": self.module.params["name"],
            "state": "Deleted",
        }

        self.module.exit_json(**self.result)

    def handle_power_status(self):
        """Handles starting, stopping, and restarting servers"""
        # check if the server exist
        server_to_change_state = self._get_server_by_name()
        if not server_to_change_state:
            #  check mode, server might not be created yet
            if self.module.check_mode:
                self.module.exit_json(changed=True)
            self.module.fail_json(msg="ERROR: server does not exist.")

        requested_server_state = self.module.params.get("state")

        body = OrderedDict()
        body["name"] = self.module.params["name"]

        # get the current server state to check if task can be skipped
        current_server_state = self.sh_api.api_query(
            path="/server/get_state.json",
            query_params={"name": self.module.params["name"]},
        )["return"]["state"]

        # if server is the requested state already, skip task
        if (
            AnsibleSitehostServer._SERVER_STATE_MAP[current_server_state]
            == requested_server_state
        ):
            self.result["msg"] = (
                f"server already {AnsibleSitehostServer._SERVER_STATE_MAP[current_server_state]}",
            )
            self.result["server"] = {
                "name": self.module.params["name"],
                "label": server_to_change_state["label"],
                "state": current_server_state,
            }
            self.module.exit_json(**self.result)
        #  check mode
        if self.module.check_mode:
            self.module.exit_json(changed=True)

        # the server state is different from requested state, start/stop server

        body["state"] = AnsibleSitehostServer._API_STATE_MAP[requested_server_state]

        state_change_job = self.sh_api.api_query(
            path="/server/change_state.json", method="POST", data=body
        )
        self.sh_api.wait_for_job(job_id=state_change_job["return"]["job_id"])

        self.result["changed"] = True
        self.result["msg"] = f"Server {self.module.params['state']} successfully"
        self.result["server"] = {
            "label": server_to_change_state["label"],
            "name": self.module.params["name"],
            "state": self._get_server_by_name()["state"],
        }

        self.module.exit_json(**self.result)

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

        api_result = self.sh_api.api_query(
            path="/server/provision.json",
            method="POST",
            data=body,
        )

        job_type = (
            SCHEDULER_JOB_TYPE
            if self.module.params["product_code"] in CLOUD_CONTAINER_SERVER_PRODUCT_CODE
            else DAEMON_JOB_TYPE
        )

        self.sh_api.wait_for_job(
            job_id=api_result["return"]["job_id"], job_type=job_type
        )

        if job_type == DAEMON_JOB_TYPE:  #  Non Cloud Container server provisioned
            self.result["msg"] = (
                f"server created: {api_result['return']['name']},"
                f" with user: root and password: {api_result['return']['password']}"
            )
            self.result["server"]["password"] = api_result["return"]["password"]

        else:  #  Cloud Container server provisioned
            self.result[
                "msg"
            ] = f"Cloud Container server {api_result['return']['name']} created"

        self.result["server"] = self._get_server_by_name(api_result["return"]["name"])
        self.result["changed"] = True

        self.module.exit_json(**self.result)

    def upgrade(self):
        """
        upgrades the server, called when server name is provided and server exists
        It will first stage the upgrade then commit the upgrade with the api, restarts server
        """
        server_to_upgrade = self._get_server_by_name()
        # check if the server exist
        if not server_to_upgrade:
            # check mode, the server may had been created earlier
            if self.module.check_mode:
                self.module.exit_json(changed=True)
            self.module.fail_json(msg="ERROR: Server does not exist.")

        # check if server plan is same as inputed product code
        if server_to_upgrade["product_code"] == self.module.params["product_code"]:
            self.module.exit_json(
                msg="Requested product is the same as current server product.",
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

        self.sh_api.wait_for_job(upgrade_job["return"]["job_id"])

        server_after_upgrade = self._get_server_by_name()

        self.result["msg"] = f"{server_after_upgrade['name']} successfully upgraded"
        self.result["server"] = server_after_upgrade
        self.result["changed"] = True

        self.module.exit_json(**self.result)

    def create_or_upgrade(self):
        if self.module.params.get("name"):  # if server name exist, upgrade the server
            self.upgrade()

        # else if label only, create the new server
        elif self.module.params.get("label"):
            self.create()
        else:  # something is wrong with the code
            self.module.fail_json(msg="ERROR: no name or label given, exiting")

    def _get_server_by_name(self, server_name=None):
        """
        return basic server information by its server name

        :params server_name: select the server to retrive, if not set, then it will get the server specified by the "name" parameter.
        :returns: information about the server, returns None if server does not exist
        :rtype: dict or None
        """
        if server_name is None:
            server_name = self.module.params.get("name")

        retrieved_server = self.sh_api.api_query(
            path="/server/get_server.json",
            query_params=OrderedDict({"name": server_name}),
            skip_status_check=True,
        )

        # if server exist, return it
        return retrieved_server["return"] if retrieved_server["status"] else None


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
        )  # type: ignore
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        required_if=(
            ("state", "present", ("product_code",)),
            ("state", "absent", ("name",)),
            ("state", "started", ("name",)),
            ("state", "stopped", ("name",)),
            ("state", "restarted", ("name",)),
        ),
        mutually_exclusive=[("label", "name")],
        required_by={"label": ("location", "product_code", "image")},
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
