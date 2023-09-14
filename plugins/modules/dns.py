#!/usr/bin/python

# Copyright: (c) 2018, Terry Jones <terry.jones@example.org>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

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
# extends_documentation_fragment:
#     - my_namespace.my_collection.my_doc_fragment_name

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

class AnsibleSitehostDNS:
    def __init__(self, module, api):
        self.sh_api = api
        self.module = module
        self.result = {
            "changed": False,
            "DNS": dict(),
        }
    
    def update_or_add(self):
        if self.module.params["record_id"]:
            self.update()
        else:
            self.add_dns_record()

    def absent(self):
        if self.module.params["record_id"]:
            self.delete_dns_record()
        else:
            self.delete_zone()

    def update(self):
        """use to update exisiting DNS record"""
        if not self.get_domain():
            self.module.fail_json(msg="ERROR: DNS zone does not exist.")
        record_to_modify = self.get_record_by_id()
        if not record_to_modify:
            self.module.fail_json(msg="ERROR: DNS Record does not exist.")

        # update the DNS record
        body=OrderedDict()
        body['domain']=self.module.params["domain"]
        body['record_id']=self.module.params["record_id"]
        body['type']=self.module.params["type"]
        body['name']=self.module.params['name']
        body['content']=self.module.params['content']
        body["prio"]=self.module.params['priority']

        update_result = self.sh_api.api_query(path="/dns/update_record.json", method="POST", data=body)
        
        if not update_result['status']: #  update failed due to incorrect parameters
            self.module.fail_json(msg=update_result['msg'])
        
        self.result["msg"] = "DNS record sucessfully updated"
        self.result["DNS"] = self.get_record_by_id()
        self.module.exit_json(**self.result)


    def add_dns_record(self):
        """add DNS record, will create DNS zone if does not exist"""
        # create DNS zone if it does not exist
        if not self.get_domain():
            self.create_zone(self.module.params["domain"])

        # create the DNS record
        body=OrderedDict()
        body["domain"]=self.module.params["domain"]
        body["type"]=self.module.params["type"]
        body["name"]=self.module.params["name"]
        body["content"]=self.module.params["content"]

        add_result = self.sh_api.api_query(path="/dns/add_record.json", method="POST", data=body)
        if not add_result['status']: #  adding failed due to incorrect parameters
            self.module.fail_json(msg=add_result['msg'])

        # get the DNS record to show in output of module
        listofrecords = self.sh_api.api_query(path="/dns/list_records.json", method="GET", query_params={"domain":self.module.params["domain"]})["return"]
        listofrecords = filter(lambda x:x["name"]==self.module.params["name"],listofrecords)
        new_record = max(listofrecords, key = lambda x:int(x["change_date"]))
        
        self.result["msg"]=f"DNS record created with id: {new_record['id']}"
        self.result["DNS"]=new_record
        self.module.exit_json(**self.result)

    def create_zone(self,domain=None):
        """create a DNS zone"""
        if domain is None:
            domain = self.module.params["domain"]
        
        body=OrderedDict()
        body['domain']=self.module.params["domain"]
        apiresult = self.sh_api.api_query(path="/dns/create_domain.json",method="POST", data=body)

        return apiresult
    
    def delete_dns_record(self):
        """deletes a DNS record"""
        if not self.get_domain():
            self.module.fail_json(msg="ERROR: DNS zone does not exist.")
        record_to_delete = self.get_record_by_id()
        if not record_to_delete:
            self.module.fail_json(msg="ERROR: DNS Record does not exist.")

        # delete the dns record
        body=OrderedDict()
        body["domain"]=self.module.params["domain"]
        body["record_id"]=self.module.params["record_id"]
        self.sh_api.api_query(path="/dns/delete_record.json", method="POST", data=body)

        self.result["msg"]="DNS record deleted"
        self.module.exit_json(**self.result)


    def get_record_by_id(self,recordid=None):
        """get the DNS record by ID"""
        if recordid is None:
            recordid=self.module.params["record_id"]

        retrieved_records=self.sh_api.api_query(path="/dns/list_records.json", method='GET', query_params = OrderedDict({"domain":self.module.params["domain"]}))
        dns_record = [record for record in retrieved_records["return"] if record["id"] == str(recordid)]

        return dns_record if dns_record else None
    
    def get_domain(self, zone=None):
        """get the DNS zone given by domain parameters"""
        if zone is None:
            zone = self.module.params["domain"]
        
        retrieved_zone=self.sh_api.api_query(path="/dns/search_domains.json", method='POST', query_params = OrderedDict({"query[domain]":zone}))["return"]

        return retrieved_zone if retrieved_zone else None
    
    def format_parameters(self):
        """ensures that the parameters are lower case"""
        if self.module.params["domain"]:
            self.module.params["domain"] = self.module.params["domain"].lower()
        if self.module.params["name"]:
            self.module.params["name"] = self.module.params["name"].lower()
    
    


def main():
    argument_spec = SitehostAPI.sitehost_argument_spec()
    argument_spec.update(
        dict(
            domain=dict(type="str"),
            record_id=dict(type="int"),
            name=dict(type="str"),
            type=dict(
                type="str", 
                choices=["A","AAAA","CNAME","MX","TXT","CAA","SRV"],
            ),
            priority=dict(type="int"),
            content=dict(type="str"),
            state=dict(type="str", choices=["present","absent"]),
        )
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
    )
    
    sitehost_api = SitehostAPI(
        module=module,
        api_key=module.params["api_key"],
        api_client_id=module.params["api_client_id"],
    )

    sitehostdns = AnsibleSitehostDNS(module=module, api=sitehost_api)

    sitehostdns.format_parameters()

    state = module.params["state"]

    if state == "present":
        sitehostdns.update_or_add()
    else:  # state is absent
        sitehostdns.absent()
        

if __name__ == '__main__':
    main()

