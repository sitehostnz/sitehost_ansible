#!/usr/bin/python

# Copyright: (c) 2018, Terry Jones <terry.jones@example.org>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import absolute_import, division, print_function

__metaclass__ = type

HTTP_GET = "GET"
HTTP_POST = "POST"

# DOCUMENTATION = r'''
# ---
# module: stack

# version_added: "1.2.0"

# short_description: Manages Cloud Containers

# description: Used for creating, deleting, updating, starting, and stopping Cloud Containers on your SiteHost account.
# author:
#   - "SiteHost Developers (developers@sitehost.co.nz)"

# options:
#     server:
#         description: The Cloud Container server to operate on.
#         required: true
#         type: str
#     name:
#         description:
#             - A unique Hash assigned to the server
#             - Generate it before hand before using it.
#         required: false
#         type: str
#     label:
#         description: Name provided by the user to the server.
#         required: false
#         type: str
#     docker_compose:
#         description:
#             - The docker_compose file that needs to be set when creating a server.
#             - Check out the documentation in the L(SiteHost Ansible Github repo,https://github.com/sitehostnz/sitehost_ansible/blob/main/docs/stack.md) to learn more about setting up a docker_compose file for Cloud Containers.
#         required: false
#         type: yaml
#     state:
#         description:
#             - Desired state of Cloud Container.
#             - C(present) will either update or create a Cloud Container.
#             - C(absent) will delete a Cloud Container.

# '''

# EXAMPLES = r'''
# # Pass in a message
# - name: Test with a message
#   my_namespace.my_collection.my_test:
#     name: hello world

# # pass in a message and have changed true
# - name: Test with a message and changed output
#   my_namespace.my_collection.my_test:
#     name: hello world
#     new: true

# # fail the module
# - name: Test failure of the module
#   my_namespace.my_collection.my_test:
#     name: fail me
# '''

# RETURN = r'''
# # These are examples of possible return values, and in general should use other names for return values.
# original_message:
#     description: The original name param that was passed in.
#     type: str
#     returned: always
#     sample: 'hello world'
# message:
#     description: The output message that the test module generates.
#     type: str
#     returned: always
#     sample: 'goodbye'
# '''

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
            # container already exist, update it
            self.update_stack()
        else:
            # otherwiser create the container.
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
            path="/cloud/stack/add.json", method=HTTP_POST, data=body
        )

        # check if the operation succeeded or not
        if not api_result["status"]:
            # code 409 means that the container name/label already exist, skip task
            if "code: 409" in api_result["msg"]:
                self.module.exit_json(msg=api_result["msg"], changed=False)

            # otherwise other error occured.
            self.module.fail_json(msg=api_result["msg"])

        self.sh_api.wait_for_job(
            job_id=api_result["return"]["job_id"], job_type="scheduler"
        )

        self.result["msg"] = f"Container {self.module.params['name']} created"
        self.result["stack"] = self._get_stack()
        self.result["changed"] = True

        self.module.exit_json(**self.result)

    def update_stack(self):
        """Updates a Cloud Container."""
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

        # check if update is successful or not
        if not api_result["status"]:
            self.module.fail_json(msg=api_result["msg"])

        # if a scheduler job is created, wait for it
        if api_result.get("return"):
            self.sh_api.wait_for_job(
                job_id=api_result["return"]["job_id"], job_type="scheduler"
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

        # deletes the Cloud Container
        api_result = self.sh_api.api_query(
            path="/cloud/stack/delete.json", method=HTTP_POST, data=body
        )

        # check if the container is already deleted
        if not api_result["status"]:
            self.module.exit_json(
                msg=f"Container {self.module.params['msg']} does not exist",
                changed=False,
            )

        self.sh_api.wait_for_job(
            job_id=api_result["return"]["job_id"], job_type="scheduler"
        )

        self.result["msg"] = f"Container {self.module.params['name']} deleted"
        self.result["changed"] = True

        self.module.exit_json(**self.result)

    def _get_stack(self, container_to_check=None):
        """
        Get Cloud Container information.

        :params container_to_check: select the container to get, if not provided.
        :return: Information on the container. If container does not exist, then
                none is returned.
        :rtype: dict
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

        # always restart the container when requested
        if requested_stack_state == "restarted":
            #  check mode
            if self.module.check_mode:
                self.module.exit_json(changed=True)
            body = OrderedDict()
            body["server"] = self.module.params["server"]
            body["name"] = self.module.params["name"]

            api_result = self.sh_api.api_query(
                path="/cloud/stack/restart.json", method=HTTP_POST, data=body
            )

            self.sh_api.wait_for_job(
                job_id=api_result["return"]["job_id"], job_type="scheduler"
            )

            self.result["msg"] = f"Container {self.module.params['name']} restarted"
            self.result["stack"] = self._get_stack()
            self.result["changed"] = True
            self.module.exit_json(**self.result)

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

        # start or stop container
        if requested_stack_state == "started":
            api_result = self.sh_api.api_query(
                path="/cloud/stack/start.json", method=HTTP_POST, data=body
            )
        else:
            api_result = self.sh_api.api_query(
                path="/cloud/stack/stop.json", method=HTTP_POST, data=body
            )

        self.sh_api.wait_for_job(
            job_id=api_result["return"]["job_id"], job_type="scheduler"
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
