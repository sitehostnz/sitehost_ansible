#!/usr/bin/python

# Copyright: (c) 2018, Terry Jones <terry.jones@example.org>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import absolute_import, division, print_function

__metaclass__ = type

HTTP_GET = "GET"
HTTP_POST = "POST"

# DOCUMENTATION = r'''
# ---
# module: my_test

# short_description: This is my test module

# # If this is part of a collection, you need to use semantic versioning,
# # i.e. the version is of the form "2.5.0" and not "2.4".
# version_added: "1.0.0"

# description: This is my longer description explaining my test module.

# options:
#     name:
#         description: This is the message to send to the test module.
#         required: true
#         type: str
#     new:
#         description:
#             - Control to demo if the result of this module is changed or not.
#             - Parameter description can be a list as well.
#         required: false
#         type: bool
# # Specify this value according to your collection
# # in format of namespace.collection.doc_fragment_name
# # extends_documentation_fragment:
# #     - my_namespace.my_collection.my_doc_fragment_name

# author:
#     - Your Name (@yourGitHubHandle)
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

        body = OrderedDict()
        body["server"] = self.module.params["server"]
        body["name"] = self.module.params["name"]
        body["label"] = self.module.params["label"]
        body["enable_ssl"] = 0
        body["docker_compose"] = self.module.params["docker_compose"]

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
        body = OrderedDict()
        body["server"] = self.module.params["server"]
        body["name"] = self.module.params["name"]
        body["params[label]"] = self.module.params["label"]
        body["params[docker_compose]"] = self.module.params["docker_compose"]

        api_result = self.sh_api.api_query(
            path="/cloud/stack/update.json", method=HTTP_POST, data=body
        )

        # check if update is sucessfull or not
        if not api_result["status"]:
            self.module.fail_json()

        self.sh_api.wait_for_job(
            job_id=api_result["return"]["job_id"], job_type="scheduler"
        )

        self.result["msg"] = f"Container f{self.module.params['name']} updated"
        self.result["stack"] = self._get_stack()
        self.result["changed"] = True

        self.module.exit_json(**self.result)

    def delete_stack(self):
        """Deletes a Cloud Container."""
        body = OrderedDict()
        body["server"] = self.module.params["server"]
        body["name"] = self.module.params["name"]

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
        """Get Cloud Container information."""
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

        if self._get_stack() is None:
            self.module.fail_json(msg="ERROR: Specified container does not exist")

        requested_stack_state = self.module.params["state"]

        # always restart the server when requested
        if requested_stack_state == "restarted":
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

        # requested container state is different from current state

        body = OrderedDict()
        body["server"] = self.module.params["server"]
        body["name"] = self.module.params["name"]

        # start or stop containers
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
        server=dict(type="str"),
        name=dict(type="str"),
        label=dict(type="str"),
        docker_compose=dict(type="str"),
        state=dict(type="str"),
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
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
