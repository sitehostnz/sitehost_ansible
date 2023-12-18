#!/usr/bin/python

# Copyright: (c) 2018, Terry Jones <terry.jones@example.org>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import absolute_import, division, print_function

__metaclass__ = type

DNS_TYPE_LIST = ["A", "AAAA", "CNAME", "MX", "TXT", "CAA", "SRV"]
HTTP_GET = "GET"
HTTP_POST = "POST"

DOCUMENTATION = r"""
---
module: dns

short_description: Manage DNS zones and records

version_added: "1.1.0"

description: Used for creating, deleting and updating DNS records and DNS zones on your SiteHost accout.

author:
  - "SiteHost Developers (developers@sitehost.co.nz)"

options:
    state:
        description: 
            - Desired state of the DNS zone / record.
            - C(present) will either upgrade or create a DNS zone or record.
            - C(absent) will delete a DNS zone or record.
        required: true
        type: str
    domain:
        description:
            - The selected DNS zone.
            - If DNS zone does not exist when adding a new DNS record, it will be automatically created.
        required: True
        type: str
        aliases: 
            - zone
            - dns_zone
    record_id:
        description:
            - The id of an exisiting DNS record to update or delete.
        type: int
    name:
        description:
            - The host name, alias, or service being defined by the record.
            - Please use the FQDN instead of relative names like C(@) or C(www)
        type: str
    type:
        description:
            - The type of record you would like to use.
        choices: [A,AAAA,CNAME,MX,TXT,CAA,SRV]
        type: str
    priority:
        description:
            - The priority of the host for C(SRV,MX) records.
        type: int
    content:
        description:
            - This is the value of the record, depending on the record type.
        type: str
"""

EXAMPLES = r"""
# Create a DNS record and print the record id
- name: create an A dns record for @
    sitehost.cloud.dns:
        domain: mydomain.co.nz
        type: A
        name: mydomain.co.nz
        content: 255.255.255.255
        api_client_id: "{{ CLIENT_ID }}"
        api_key: "{{ USER_API_KEY }}"
        state: present
    register: recordouput

- name: print the record id
    ansible.builtin.debug:
        var: recordouput.dns.id

# Update a previously created dns record
- name: update previously created record
    sitehost.cloud.dns:
        domain: mydomain.co.nz
        record_id: 1234567
        type: A
        name: new.mydomain.co.nz
        content: 255.255.255.254
        api_client_id: "{{ CLIENT_ID }}"
        api_key: "{{ USER_API_KEY }}"
        state: present

# Delete a previously created DNS record
- name: Delete dns record
    sitehost.cloud.dns:
        domain: mydomain.co.nz
        record_id: 1234567
        api_client_id: "{{ CLIENT_ID }}"
        api_key: "{{ USER_API_KEY }}"
        state: absent

# create a DNS zone without adding any records
- name: create DNS zone
    sitehost.cloud.dns:
        domain: newdomain.com
        api_client_id: "{{ CLIENT_ID }}"
        api_key: "{{ USER_API_KEY }}"
        state: present

# delete a DNS zone
- name: delete DNS zone
    sitehost.cloud.dns:
        domain: newdomain.com
        api_client_id: "{{ CLIENT_ID }}"
        api_key: "{{ USER_API_KEY }}"
        state: absent
"""

RETURN = r"""
dns:
    description: The dns record being created or modified.
    type: dict
    returned: success
    sample: {
        "change_date": "1695252962",
        "content": 255.255.255.255",
        "id": "1234567",
        "name": "www.mydomain.co.nz",
        "prio": "0",
        "state": "0",
        "ttl": "3600",
        "type": "A"
    }
msg:
    description: A short messages showing the state of the module execution.
    type: str
    returned: always
    sample: "DNS record created with id: 1234567"
"""

from collections import OrderedDict  # noqa: E402

from ansible.module_utils.basic import AnsibleModule  # noqa: E402

from ..module_utils.sitehost import SitehostAPI  # noqa: E402


class AnsibleSitehostDNS:
    def __init__(self, module, api):
        self.sh_api = api
        self.module = module
        self.result = {
            "changed": False,
            "dns": dict(),
        }

    def update_or_add(self):
        """Check if the current dns record needs to be updated or a new dns zone
        or record needs to be created when state is set to present."""
        if self.module.params["record_id"]:
            self.update_dns_record()
        elif not self.module.params["name"]:
            self.create_domain()
        else:
            self.add_dns_record()

    def absent(self):
        """Check if the DNS record or zone needs to be deleted when the state
        is set to absent."""
        if self.module.params["record_id"]:
            self.delete_dns_record()
        else:
            self.delete_domain()

    def update_dns_record(self):
        """Update an existing DNS record."""
        #  check mode
        if self.module.check_mode:
            self.module.exit_json(changed=True)

        if not self._get_domain():
            self.module.fail_json(msg="ERROR: DNS zone does not exist.")
        if not self._get_record_by_id():
            self.module.fail_json(msg="ERROR: DNS Record does not exist.")

        # update the DNS record
        body = OrderedDict()
        body["domain"] = self.module.params["domain"]
        body["record_id"] = self.module.params["record_id"]
        body["type"] = self.module.params["type"]
        body["name"] = self.module.params["name"]
        body["content"] = self.module.params["content"]
        body["prio"] = self.module.params["priority"]

        update_result = self.sh_api.api_query(
            path="/dns/update_record.json", method=HTTP_POST, data=body
        )

        if "status" in update_result and not update_result["status"]:  # update failed due to incorrect parameters
            self.module.fail_json(msg=update_result["msg"])

        self.result["msg"] = "DNS record successfully updated"
        self.result["dns"] = self._get_record_by_id()
        self.result["changed"] = True
        self.module.exit_json(**self.result)

    def add_dns_record(self):
        """Adds a DNS record, will create DNS zone if it does not exist."""
        # check mode
        if self.module.check_mode:
            self.module.exit_json(changed=True)

        # create DNS zone if it does not exist
        if self._get_domain() is None:
            self._create_zone(self.module.params["domain"])

        # create the DNS record
        body = OrderedDict()
        body["domain"] = self.module.params["domain"]
        body["type"] = self.module.params["type"]
        body["name"] = self.module.params["name"]
        body["content"] = self.module.params["content"]

        add_result = self.sh_api.api_query(
            path="/dns/add_record.json", method=HTTP_POST, data=body
        )
        if "status" in add_result and not add_result["status"]:  # adding failed due to incorrect parameters
            self.module.fail_json(msg=add_result["msg"])

        # get the newly created DNS record to show in output of module
        record_list = self.sh_api.api_query(
            path="/dns/list_records.json",
            method=HTTP_GET,
            query_params={"domain": self.module.params["domain"]},
        )
        if "return" not in record_list:
            self.module.fail_json(msg=record_list)

        return_record_list = record_list["return"]
        return_record_list = filter(
            lambda x: x["name"] == self.module.params["name"], return_record_list
        )
        new_record = max(return_record_list, key=lambda x: int(x["change_date"]))

        self.result["msg"] = f"DNS record created with id: {new_record['id']}"
        self.result["dns"] = new_record
        self.result["changed"] = True
        self.module.exit_json(**self.result)

    def delete_domain(self):
        """Deletes a DNS zone."""
        # check mode
        if self.module.check_mode:
            self.module.exit_json(changed=True)

        # check if domain zone exists
        if self._get_domain() is None:
            self.module.exit_json(msg="Specified DNS zone does not exist")

        # delete the zone
        body = OrderedDict()
        body["domain"] = self.module.params["domain"]

        delete_result = self.sh_api.api_query(path="/dns/delete_domain.json", method=HTTP_POST, data=body)
        if "status" in delete_result and not delete_result["status"]:
            self.module.fail_json(msg=delete_result)

        self.module.exit_json(msg="DNS zone deleted", changed=True)

    def create_domain(self):
        """Creates a new DNS zone only when there is no DNS records specified."""
        if self._get_domain():
            self.module.exit_json(msg="DNS zone already exist")

        # check mode
        if self.module.check_mode:
            self.module.exit_json(changed=True)

        create_result = self._create_zone()

        if "status" in create_result and not create_result["status"]:
            self.module.fail_json(msg=create_result["msg"])

        self.result["msg"] = f"DNS zone \"{self.module.params['domain']}\" created"
        self.result["changed"] = True

        self.module.exit_json(**self.result)

    def delete_dns_record(self):
        """Deletes a DNS record."""
        # check mode
        if self.module.check_mode:
            self.module.exit_json(changed=True)

        if self._get_domain() is None:
            self.module.fail_json(msg="ERROR: DNS zone does not exist.")
        if self._get_record_by_id() is None:
            self.module.exit_json(msg="DNS Record does not exist.", changed=False)

        # delete the dns record
        body = OrderedDict()
        body["domain"] = self.module.params["domain"]
        body["record_id"] = self.module.params["record_id"]
        self.sh_api.api_query(
            path="/dns/delete_record.json", method=HTTP_POST, data=body
        )

        self.result["msg"] = "DNS record deleted"
        self.result["changed"] = True
        self.module.exit_json(**self.result)

    def _get_record_by_id(self, record_id=None):
        """
        Get the DNS record by ID.

        :param record_id: The dns record to retrieve. If it is not set,
                    then use `record_id` parameter in playbook.
        :returns: The DNS record if it exists, otherwise return none.
        :rtype: list or None
        """
        if record_id is None:
            record_id = self.module.params["record_id"]

        retrieved_records = self.sh_api.api_query(
            path="/dns/list_records.json",
            method=HTTP_GET,
            query_params=OrderedDict({"domain": self.module.params["domain"]}),
        )
        dns_record = [
            record
            for record in retrieved_records["return"]
            if record["id"] == str(record_id)
        ]

        return dns_record if dns_record else None

    def _get_domain(self, zone=None):
        """
        Get the DNS zone given by domain parameters.

        :param zone: The dns zone to retrieve. If it is not set,
                    then use `domain` parameter in playbook.
        :returns: The Zone information if it exists, otherwise
                    return none
        :rtype: dict or None
        """
        if zone is None:
            zone = self.module.params["domain"]

        body = OrderedDict()
        body["query[domain]"] = zone
        retrieved_zone = self.sh_api.api_query(
            path="/dns/search_domains.json", method=HTTP_POST, data=body
        )["return"]

        return retrieved_zone if retrieved_zone else None

    def format_parameters(self):
        """ensures that the parameters are lower case"""
        if self.module.params["domain"]:
            self.module.params["domain"] = self.module.params["domain"].lower()
        if self.module.params["name"]:
            self.module.params["name"] = self.module.params["name"].lower()

    def _create_zone(self, domain=None):
        """
        Create a DNS zone.

        :params domain: Specifies the DNS zone to create. If it is not set,
                    then use `domain` parameter in playbook
        :returns: The api output.
        :rtype: dict
        """
        # check mode
        if self.module.check_mode:
            self.module.exit_json(changed=True)

        if domain is None:
            domain = self.module.params["domain"]

        body = OrderedDict()
        body["domain"] = domain
        api_result = self.sh_api.api_query(
            path="/dns/create_domain.json", method=HTTP_POST, data=body
        )

        return api_result


def main():
    argument_spec = SitehostAPI.sitehost_argument_spec()
    argument_spec.update(
        dict(
            domain=dict(type="str", required=True, aliases=["zone", "dns_zone"]),
            record_id=dict(type="int"),
            name=dict(type="str"),
            type=dict(
                type="str",
                choices=DNS_TYPE_LIST,
            ),
            priority=dict(type="int"),
            content=dict(type="str"),
            state=dict(
                type="str",
                choices=["present", "absent"],
                default="present",
            ),
        )
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        required_together=("name", "type", "content"),
        supports_check_mode=True,
    )

    sitehost_api = SitehostAPI(
        module=module,
        api_key=module.params["api_key"],
        api_client_id=module.params["api_client_id"],
    )

    sitehost_dns = AnsibleSitehostDNS(module=module, api=sitehost_api)

    sitehost_dns.format_parameters()

    state = module.params["state"]

    if state == "present":
        sitehost_dns.update_or_add()
    else:  # state is absent
        sitehost_dns.absent()


if __name__ == "__main__":
    main()
