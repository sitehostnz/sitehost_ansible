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

    def absent(self):
        """deletes a server
        Overloading parent class method as a test right now
        """
        server_to_delete = self.get_server_by_name()

        if server_to_delete: # server exist, deleting newest server
            deleteresult = self.api_query(path = "/server/delete.json", query_params={
                "name":server_to_delete["name"]
            })

            delete_job_result=self.wait_for_job(job_id=deleteresult["return"]["job_id"]) # pause execution until the server is fully deleted

            self.result["changed"] = True

            self.result["diff"]["before"] = server_to_delete
            self.result["diff"]["after"] = delete_job_result
            self.result["message"]=delete_job_result["message"]

            self.module.exit_json(**self.result)
        else:  # server does not exist, so just skip and continue
            self.result["skipped"] = True
            self.module.exit_json(msg="Server does not exist, skipping task.",**self.result)


    def handle_power_status(self):
        """this handles starting, stopping, and restarting servers"""
        requested_server_state = self.module.params.get("state")
        if requested_server_state == "restarted":  # always restart server when requested
            
            body = OrderedDict()
            body["name"]=self.module.params.get("name")
            body["state"]="reboot"

            restart_result=self.api_query(path="/server/change_state.json", method="POST", data=body )

            restart_job=self.wait_for_job(job_id=restart_result["return"]["job_id"])
            self.module.exit_json(changed=True, job_status= restart_job)
        
        else:  # it is not a restarted state, check if it needs to turn server on or off
            current_server_state = self.api_query(path="/server/get_state.json", query_params={
                "name":self.module.params.get("name")
            })["return"]["state"]

            if (current_server_state == "On" and requested_server_state == "started"):  # check if the server is on
                self.module.exit_json(skipped=True, msg="server already started, skipped task", **self.result)
            elif (current_server_state == "Off" and requested_server_state == "stopped"):  # check if server is off
                self.module.exit_json(skipped=True, msg="server already stopped, skipped task", **self.result)
            else:  # the server state is different from requetsed state, start/stop server
                if(requested_server_state == "started"):  # start server up
                    body=OrderedDict()
                    body["name"]=self.module.params.get("name")
                    body["state"]="power_on"

                    startjob=self.api_query(path="/server/change_state.json", method="POST", data=body)
                    startresult=self.wait_for_job(job_id=startjob["return"]["job_id"])

                    self.module.exit_json(changed=True,job_status=startresult)

                elif(requested_server_state == "stopped"):  # stop the server
                    body=OrderedDict()
                    body["name"]=self.module.params.get("name")
                    body["state"]="power_off"

                    offjob=self.api_query(path="/server/change_state.json", method="POST", data=body)
                    offresult=self.wait_for_job(job_id=offjob["return"]["job_id"])

                    self.module.exit_json(changed=True,job_status=offresult)
            self.module.fail_json(msg="an unexpected error occured", requested_state = requested_server_state, current_server_state = current_server_state)

                


    def create(self):
        data = OrderedDict()

        data["label"] = self.module.params["label"]
        data["location"] = self.module.params["location"]
        data["product_code"] = self.module.params["product_code"]
        data["image"] = self.module.params["image"]
        data["params[ipv4]"] = "auto"

        self.result["changed"] = True
        resource = dict()

        self.result["diff"]["before"] = dict()
        self.result["diff"]["after"] = data

        if not self.module.check_mode:
            resource = self.api_query(
                path="/server/provision.json",
                method="POST",
                data=data,
            )

            if resource:
                self.wait_for_job(job_id=resource["return"]["job_id"], state="Completed")

        self.module.exit_json(**self.result)

    def upgrade(self):
        """
        upgrades the server, called when server name is provided and server exists
        It will first stage the upgrade then commit the upgrade with the api, restarts server
        """
        server_to_upgrade = self.get_server_by_name()
        if(server_to_upgrade["product_code"] == self.module.params.get("product_code")):  # check if server plan is same as inputed product code
            self.module.exit_json(skipped=True, msg="Requested product is the same as current server product, skipping.")
        
        
        body = OrderedDict()
        body["name"]=self.module.params.get("name")
        body["plan"]=self.module.params.get("product_code")
        self.api_query(path="/server/upgrade_plan.json", method="POST", data=body)  # stage server upgrade
        
        body = OrderedDict()
        body["name"]=self.module.params.get("name")
        upgrade_job = self.api_query(path="/server/commit_disk_changes.json", method="POST", data=body)  # commit upgrade, will restart server

        job_result=self.wait_for_job(upgrade_job["return"]["job_id"])

        server_after_upgrade = self.get_server_by_name()

        self.result["diff"]["before"] = server_to_upgrade
        self.result["diff"]["after"] = server_after_upgrade
        self.result["job_result"] = job_result
        self.result["msg"] = job_result["message"]
        self.result["changed"] = True

        self.module.exit_json(**self.result)


        

    def create_or_update(self):
        if self.module.params.get("name"): # if server name exist, upgrade the server
            self.upgrade()
        elif self.module.params.get("label"): # else if label only, create the new server
            self.create()
        else: # something is wrong with the code
            self.module.fail_json(msg="ERROR: no name or label given, exiting")
    
    def present(self):
        self.create_or_update()

    def transform_result(self, resource):
        """currently does nothing"""
        return resource
    
    def get_servers_by_label(self, server_label=None, sort_by = "created"):
        """
        uses sitehost api to return all servers excatly matching the server label given in the module argument

        :param sort_by: defaults to "created", use to to set how the server is sorted. example: "state", "maint_date", "name"
        """
        if server_label is None:
            server_label = self.module.params.get("label") # get the server label user given
        

        # get list of servers that potentially matches the user given server label
        list_of_servers  = self.api_query(path = "/server/list_servers.json",
            query_params=OrderedDict([
                ("filters[name]", server_label),
                ("filters[sort_by]", sort_by),
                ("filters[sort_dir]", "desc")
            ])
        )["return"]["data"]
        
        # since sitehost api return all servers losely matching the given server label
        # this will filter out all servers that does not excatly match the given server label
        list_of_servers = list(filter(lambda x:x["label"]==server_label, list_of_servers))

        return list_of_servers
    
    def get_server_by_name(self, server_name=None):
        """return a server by its server name"""
        if server_name is None:
            server_name = self.module.params.get("name")

        return self.api_query(path = "/server/get_server.json", query_params=OrderedDict({
          "name":server_name
      }))["return"]

def main():
    argument_spec = sitehost_argument_spec()
    argument_spec.update(
        dict(
            label=dict(type="str"),
            name=dict(type="str"),
            location=dict(type="str"),
            product_code=dict(type="str"),
            image=dict(type="str"),
            # ssh_keys=dict(type="list", elements="str", no_log=False),
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

    sitehost = AnsibleSitehostServer(
        module=module,
        namespace="sitehost_server",
        api_key=module.params["api_key"],
        api_client_id=module.params["api_client_id"]
    )

    state = module.params["state"]  # type: ignore

    if state == "absent":
        sitehost.absent()
    elif state == "present":
        sitehost.present()
    else:
        sitehost.handle_power_status()

if __name__ == "__main__":
    main()
