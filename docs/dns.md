<p align="center">
    <a href="https://sitehost.nz" target="_blank">
        <img src="../.github/sitehost-logo.svg" height="130">
    </a>
</p>

# sitehost.cloud.dns
Manages SiteHost DNS records and zones. Make sure to checkout our [developer KB article](https://kb.sitehost.nz/developers) for more information on our API. Please ensure the `Domains: DNS` privilege is enabled your your SiteHost api key.

- [parameters](#parameter)
- [examples](#examples)
- [return](#return-values)

## Parameter

 Field     | Type | Required | Description                                                                  |
|-----------|------|----------|------------------------------------------------------------------------------|
| `state` | <center>`str`</center> | <center>Optional **(Default: present)**</center> | The desired state of the target.  **(Choices: `present`, `absent`)** |
| `domain` | <center>`str`</center> | <center>**Required**</center> | The selected DNS zone. If DNS zone does not exist when adding a new DNS record, it will be automatically created.  **(Alias: `zone`, `dns_zone`)**  |
| `record_id` | <center>`int`</center> | <center>Optional</center> | The id of an exisiting DNS record to update or delete. | 
| `name` | <center>`str`</center> | <center>Optional</center> | The host name, alias, or service being defined by the record. Please use the FQDN instead of relative names like `@` or `www`.  |
| `type` | <center>`str`</center> | <center>Optional</center> | The type of record you would like to use. **(Choices: `A`,`AAAA`,`CNAME`,`MX`,`TXT`,`CAA`,`SRV`)**  | 
| `priority` | <center>`int`</center> | <center>Optional</center> | The priority of the host for `SRV` and `MX` records. | 
| `content` | <center>`str`</center> | <center>Optional</center> | This is the value of the record, depending on the record type. |
| `api_key` | <center>`str`</center> | <center>**Required**</center> | Your SiteHost api key [generated from CP](https://kb.sitehost.nz/developers/api#creating-an-api-key). |
| `api_client_id` | <center>`int`</center> | <center>**Required**</center> | The client id of your SiteHost account. |

## Examples


- Create a DNS record and print the record id
```yml
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
```

- Update a previously created dns record
```yml
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

```
- Delete a previously created DNS record
```yml
- name: Delete dns record
    sitehost.cloud.dns:
        domain: mydomain.co.nz
        record_id: 1234567
        api_client_id: "{{ CLIENT_ID }}"
        api_key: "{{ USER_API_KEY }}"
        state: absent
```
- create a DNS zone without adding any records
```yml
- name: create DNS zone
    sitehost.cloud.dns:
        domain: newdomain.com
        api_client_id: "{{ CLIENT_ID }}"
        api_key: "{{ USER_API_KEY }}"
        state: present
```

- delete a DNS zone
```yml
- name: delete DNS zone
    sitehost.cloud.dns:
        domain: newdomain.com
        api_client_id: "{{ CLIENT_ID }}"
        api_key: "{{ USER_API_KEY }}"
        state: absent
```

## Return Values
- `dns` - Shows the details of the DNS record
    - returned: On success
    - type: dict
    - sample:
    ```yml
    "dns": {
        "change_date": "1695270226",
        "content": "255.255.255.255",
        "id": "1234567",
        "name": "mydomain.com",
        "prio": "0",
        "state": "0",
        "ttl": "3600",
        "type": "A"
    }
    ```


- `msg` - Text that indicates the status of the module
    - return: Always
    - type: str
    - sample: `DNS record created with id: 1234567`



