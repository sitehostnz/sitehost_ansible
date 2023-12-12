#!/usr/bin/python

# Copyright: (c) 2018, Terry Jones <terry.jones@example.org>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import absolute_import, division, print_function

__metaclass__ = type

HTTP_GET = "GET"
HTTP_POST = "POST"
SCHEDULER_JOB_TYPE = "scheduler"

DOCUMENTATION = r"""
---
module: stack

version_added: "1.2.0"

short_description: Manages Cloud Containers

description: Used for creating, deleting, updating, starting, and stopping Cloud Containers on your SiteHost account.

author:
  - "SiteHost Developers (developers@sitehost.co.nz)"

options:
    state:
        description:
            - Indicates the desired state of the Cloud Container.
            - C(present) will either update or create a Cloud Container.
            - C(absent) will delete a Cloud Container.
            - C(started) for powering on the container.
            - C(stopped) for powering off the container.
            - C(restarted) for restarting the container.
        default: present
        choices: [present, absent, started, stopped, restarted]
        type: str
    server:
        description: 
            - The Cloud Container server to operate on.
        required: true
        type: str
    name:
        description:
            - A unique Hash assigned to the server
            - L(Generate, https://docs.sitehost.nz/api/v1.2/?path=/cloud/stack/generate_name&action=GET) one with the API before hand before using it.
        required: false
        type: str
    label:
        description: 
            - User chosen label of the Container.
            - The label format must be a valid FQDN.
        required: false
        type: str
    docker_compose:
        description:
            - The docker_compose file that needs to be set when creating a server.
            - Check out the documentation in the L(SiteHost Ansible Github repo,https://github.com/sitehostnz/sitehost_ansible/blob/main/docs/stack.md) to learn more about setting up a docker_compose file for Cloud Containers.
        required: false
        type: yaml
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

EXAMPLES = r"""
# create a Cloud Container running apache + php 8.2
- name: create a container
  sitehost.cloud.stack:
    server: ch-mycloudse
    name: ccb7a31da52e5b47
    label: mycontainer.co.nz
    docker_compose: |
        version: '2.1'
        services:
            ccb7a31da52e5b47:
                container_name: ccb7a31da52e5b47
                environment:
                    - 'VIRTUAL_HOST=mycontainer.co.nz,www.mycontainer.co.nz'
                    - CERT_NAME=mycontainer.co.nz
                expose:
                    - 80/tcp
                image: 'registry.sitehost.co.nz/sitehost-php82-apache:4.0.1-jammy'
                labels:
                    - 'nz.sitehost.container.website.vhosts=mycontainer.co.nz,www.mycontainer.co.nz'
                    - nz.sitehost.container.image_update=True
                    - nz.sitehost.container.label=mycontainer.co.nz
                    - nz.sitehost.container.type=www
                    - nz.sitehost.container.monitored=True
                    - nz.sitehost.container.backup_disable=False
                restart: unless-stopped
                volumes:
                    - '/data/docker0/www/ccb7a31da52e5b47/crontabs:/cron:ro'
                    - '/data/docker0/www/ccb7a31da52e5b47/application:/container/application:rw'
                    - '/data/docker0/www/ccb7a31da52e5b47/config:/container/config:ro'
                    - '/data/docker0/www/ccb7a31da52e5b47/logs:/container/logs:rw'
        networks:
            default:
                external:
                    name: infra_default

    api_client_id: "{{ CLIENT_ID }}"
    api_key: "{{ USER_API_KEY }}"
    state: present

# delete a Cloud Container
- name: delete a container
  sitehost.cloud.stack:
    server: ch-mycloudse
    name: ccb7a31da52e5b47
    api_client_id: "{{ CLIENT_ID }}"
    api_key: "{{ USER_API_KEY }}"
    state: absent

# powering up a Cloud Container
- name: start container
  sitehost.cloud.stack:
    server: ch-mycloudse
    name: ccb7a31da52e5b47
    api_client_id: "{{ CLIENT_ID }}"
    api_key: "{{ USER_API_KEY }}"
    state: started

"""

RETURN = r"""
# These are examples of possible return values, and in general should use other names for return values.
msg:
    description: A short messages showing the state of the module execution.
    type: str
    returned: always
    sample: 'Container ccb7a31da52e5b47 created'
stack:
    description: The Cloud Container status.
    type: dict
    returned: success
    sample: {
        "client_id": "1234567",
        "containers": [
            {
                "backups": true,
                "container_id": "b3a1775335a7e9b9c85c835fa1a5973b19e67e7a7a4577121f8e879ffafecf80",
                "date_added": "2023-10-11 15:14:52",
                "date_updated": "2023-10-11 15:14:59",
                "image": "registry.sitehost.co.nz/sitehost-php82-apache:4.0.1-jammy",
                "is_missing": "0",
                "monitored": true,
                "name": "ccb7a31da52e5b47",
                "pending": null,
                "size": "0",
                "ssl_enabled": false,
                "state": "Up"
            }
        ],
        "date_added": "2023-10-11 15:14:52",
        "date_updated": "2023-10-11 15:14:59",
        "docker_file": "version: '2.1'\nservices:\n    ccb7a31da52e5b47:\n        container_name: ccb7a31da52e5b47\n        environment:\n            - 'VIRTUAL_HOST=mycontainer.co.nz,www.mycontainer.co.nz'\n            - CERT_NAME=mycontainer.co.nz\n        expose:\n            - 80/tcp\n        image: 'registry.sitehost.co.nz/sitehost-php82-apache:4.0.1-jammy'\n        labels:\n            - 'nz.sitehost.container.website.vhosts=mycontainer.co.nz,www.mycontainer.co.nz'\n            - nz.sitehost.container.image_update=True\n            - nz.sitehost.container.label=mycontainer.co.nz\n            - nz.sitehost.container.type=www\n            - nz.sitehost.container.monitored=True\n            - nz.sitehost.container.backup_disable=False\n        restart: unless-stopped\n        volumes:\n            - '/data/docker0/www/ccb7a31da52e5b47/crontabs:/cron:ro'\n            - '/data/docker0/www/ccb7a31da52e5b47/application:/container/application:rw'\n            - '/data/docker0/www/ccb7a31da52e5b47/config:/container/config:ro'\n            - '/data/docker0/www/ccb7a31da52e5b47/logs:/container/logs:rw'\nnetworks:\n    default:\n        external:\n            name: infra_default\n",
        "ip_addr_server": "255.255.255.255",
        "is_missing": "0",
        "label": "mycontainer.co.nz",
        "name": "ccb7a31da52e5b47",
        "pending": null,
        "server_id": "12345",
        "server_label": "my cloud server",
        "server_name": "ch-mycloudse",
        "server_owner": true
    }

"""

from collections import OrderedDict  # noqa: E402

from ansible.module_utils.basic import AnsibleModule  # noqa: E402

from ..module_utils.sitehost import SitehostAPI  # noqa: E402


class AnsibleSitehostStack:
    def __init__(self, module, api):
        self.sh_api = api
        self.module = module
        self.result = {
            "changed": False,
            "stack": dict(),
        }

    def create_or_update(self):
        if self._get_stack():
            # If the container already exists, update its configuration.
            self.update_stack()
        else:
            # otherwise create a new one.
            self.create_stack()

    def create_stack(self):
        """create a Cloud Container."""
        #  check mode
        if self.module.check_mode:
            self.module.exit_json(changed=True)

        body = OrderedDict()
        body["server"] = self.module.params["server"]
        body["name"] = self.module.params["name"]
        body["label"] = self.module.params["label"]
        body["enable_ssl"] = 0
        body["docker_compose"] = self.module.params["docker_compose"]

        # creates Cloud Container
        api_result = self.sh_api.api_query(
            path="/cloud/stack/add.json",
            method=HTTP_POST,
            data=body,
        )

        self.sh_api.wait_for_job(
            job_id=api_result["return"]["job_id"], job_type=SCHEDULER_JOB_TYPE
        )

        self.result["msg"] = f"Container {self.module.params['name']} created"
        self.result["stack"] = self._get_stack()
        self.result["changed"] = True

        self.module.exit_json(**self.result)

    def update_stack(self):
        """Updates a Cloud Container. This method updates the label and/or
        docker_compose of an existing container based on the provided parameters.
        """
        #  check mode
        if self.module.check_mode:
            self.module.exit_json(changed=True)

        body = OrderedDict()
        body["server"] = self.module.params["server"]
        body["name"] = self.module.params["name"]

        if self.module.params.get("label"):  #  update label if defined
            body["params[label]"] = self.module.params["label"]
            self.result["changed"] = True
        if self.module.params.get(
            "docker_compose"
        ):  #  update docker_compose if defined
            body["params[docker_compose]"] = self.module.params["docker_compose"]
            self.result["changed"] = True

        api_result = self.sh_api.api_query(
            path="/cloud/stack/update.json", method=HTTP_POST, data=body
        )

        # if a scheduler job is created, wait for it
        if api_result.get("return"):
            self.sh_api.wait_for_job(
                job_id=api_result["return"]["job_id"], job_type=SCHEDULER_JOB_TYPE
            )

        self.result["msg"] = f"Container {self.module.params['name']} updated"
        self.result["stack"] = self._get_stack()

        self.module.exit_json(**self.result)

    def delete_stack(self):
        """Deletes a Cloud Container."""
        #  check mode
        if self.module.check_mode:
            self.module.exit_json(changed=True)

        body = OrderedDict()
        body["server"] = self.module.params["server"]
        body["name"] = self.module.params["name"]

        # if container does not exist, then skip the task
        if self._get_stack() is None:
            self.module.exit_json(
                msg=f"Container {self.module.params['name']} does not exist",
                changed=False,
            )

        # deletes the Cloud Container
        api_result = self.sh_api.api_query(
            path="/cloud/stack/delete.json",
            method=HTTP_POST,
            data=body,
        )

        self.sh_api.wait_for_job(
            job_id=api_result["return"]["job_id"], job_type=SCHEDULER_JOB_TYPE
        )

        self.result["msg"] = f"Container {self.module.params['name']} deleted"
        self.result["changed"] = True

        self.module.exit_json(**self.result)

    def _get_stack(self, container_to_check=None):
        """
        Get Cloud Container information.

        :params container_to_check: select the container to get, if not provided.
        :return: Information about the container. Returns None if
                the container doesn't exist.
        :rtype: dict or None
        """
        if container_to_check is None:
            container_to_check = self.module.params["name"]

        retrived_container = self.sh_api.api_query(
            path="/cloud/stack/get.json",
            method=HTTP_GET,
            query_params=OrderedDict(
                [
                    ("server", self.module.params["server"]),
                    ("name", container_to_check),
                ]
            ),
            skip_status_check=True,
        )

        return retrived_container["return"] if retrived_container["status"] else None

    def handle_power_state(self):
        """Use to start, stop and restart containers"""

        # check if the container exist
        if self._get_stack() is None:
            #  check mode, container might not be created yet
            if self.module.check_mode:
                self.module.exit_json(changed=True)
            self.module.fail_json(msg="ERROR: Specified container does not exist")

        requested_stack_state = self.module.params["state"]

        # otherwise get the current container state to check if task can be skipped
        current_stack_state = self._get_stack()["containers"][0]["state"]

        stack_state_map = {"Up": "started", "Exit 0": "stopped"}

        # the container state is the requested state already, skip task.
        if stack_state_map[current_stack_state] == requested_stack_state:
            self.result["msg"] = f"Container already {requested_stack_state}"
            self.result["stack"] = self._get_stack()
            self.module.exit_json(**self.result)

        ## requested container state is different from current state

        #  check mode
        if self.module.check_mode:
            self.module.exit_json(changed=True)

        body = OrderedDict()
        body["server"] = self.module.params["server"]
        body["name"] = self.module.params["name"]

        # converts module user input to appropriate api call state
        api_state_map = {"started": "start", "stopped": "stop", "restarted": "restart"}

        # start or stop container
        api_result = self.sh_api.api_query(
            path=f"/cloud/stack/{api_state_map[requested_stack_state]}.json",
            method=HTTP_POST,
            data=body,
        )

        self.sh_api.wait_for_job(
            job_id=api_result["return"]["job_id"], job_type=SCHEDULER_JOB_TYPE
        )
        self.result[
            "msg"
        ] = f"Container {self.module.params['name']} {requested_stack_state}"
        self.result["stack"] = self._get_stack()
        self.result["changed"] = True
        self.module.exit_json(**self.result)


def main():
    argument_spec = SitehostAPI.sitehost_argument_spec()
    argument_spec.update(
        server=dict(type="str", required=True),
        name=dict(type="str", required=True),
        label=dict(type="str"),
        docker_compose=dict(type="str"),
        state=dict(
            type="str",
            choices=["present", "absent", "started", "stopped", "restarted"],
            default="present",
        ),
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
    )

    sitehost_api = SitehostAPI(
        module=module,
        api_key=module.params["api_key"],
        api_client_id=module.params["api_client_id"],
    )

    sitehoststack = AnsibleSitehostStack(module=module, api=sitehost_api)

    state = module.params["state"]

    if state == "present":
        sitehoststack.create_or_update()
    elif state == "absent":
        sitehoststack.delete_stack()
    else:
        sitehoststack.handle_power_state()


if __name__ == "__main__":
    main()
