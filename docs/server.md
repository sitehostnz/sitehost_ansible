<p align="center">
    <a href="https://sitehost.nz" target="_blank">
        <img src="../.github/sitehost-logo.svg" height="130">
    </a>
</p>

# sitehost.cloud.server
Manages SiteHost Server Instance. Make sure to checkout our [developer KB article](https://kb.sitehost.nz/developers) for more information on our API. Please ensure that the `Servers & Cloud Containers: Server` and `Servers & Cloud Containers: Job` privilege is enabled your your SiteHost API key.

- [parameters](#parameter)
- [examples](#examples)
- [return](#return-values)

## Parameter
| Field     | Type | Required | Description                                                                  |
|-----------|------|----------|------------------------------------------------------------------------------|
| `state` | <center>`str`</center> | <center>Optional **(Default: present)**</center> | The desired state of the target.  **(Choices: `present`, `absent`, `started`,`stopped`, `restarted`)** |
| `label` | <center>`str`</center> | <center>Optional</center> | User chosen label of the new server, **mutually exclusive to `name`**.  Please ensure that verbose mode `-v` is enabled to see the password of the newly created server.  |
| `name` | <center>`str`</center> | <center>Optional</center> | Unique auto generated machine name for server. Used to select servers that has **already present**.   |
| `location` | <center>`str`</center> | <center>Optional</center> | The code for the [location](https://kb.sitehost.nz/developers/api/locations) to provision the new server at. *eg. AKLCITY*   |
| `product_code` | <center>`str`</center> | <center>Optional</center> | The code for the [server specification](specification,https://kb.sitehost.nz/developers/api/product-codes) to use when provisioning the new server. *eg. XENLIT*|
| `image` | <center>`str`</center> | <center>Optional</center> | The [image](https://kb.sitehost.nz/developers/api/images) to use for the new server. *eg. ubuntu-jammy-pvh.amd64*   |
| `api_key` | <center>`str`</center> | <center>**Required**</center> | Your SiteHost API key [generated from CP](https://kb.sitehost.nz/developers/api#creating-an-api-key). |
| `api_client_id` | <center>`int`</center> | <center>**Required**</center> | The client id of your SiteHost account. |


### Restrictions

- Note that `label` is only used for creating new servers and `name` is used for selecting exisiting servers. Therefore `label` and `name` **cannot be defined at the same time**.
- `location`, `product_code`, `image` are used only for creating new servers. Therefore they **must be present** if `label` is defined.

### `api key` and `api_client_id` environment variable

Instead of defining the `api_key` and `api_client_id`, you can set up them up as environment variables:
```bash
export SH_API_KEY=your_api_key
export SH_CLIENT_ID=your_client_id
``` 

## Examples

- Creating a VPS, use `-v` as argument when running the playbook to see password:
```yml
- name: create a 1 core VPS with ubuntu jammy image
  sitehost.cloud.server:
    label: myserver
    location: AKLCITY
    product_code: XENLIT
    image: ubuntu-jammy-pvh.amd64
    api_client_id: "{{ CLIENT_ID }}"
    api_key: "{{ USER_API_KEY }}"
    state: present
```

- Create a VPS and register its output to shserver and outputs the password with debug:
```yml
- name: create a 1 core VPS with ubuntu jammy image
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
```

- Creating a server then upgrading it.
```yml
- name: create a 1 core VPS with ubuntu jammy image
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
```

- Restarts the previously created server
```yml
- name: restart server
  sitehost.cloud.server:
    name: "{{ shserver.server.name }}"
    api_client_id: "{{ CLIENT_ID }}"
    api_key: "{{ USER_API_KEY }}"
    state: restarted
```

- Deletes server 
```yml
- name: delete server
  sitehost.cloud.server:
    name: "{{ shserver.server.name }}"
    api_client_id: "{{ CLIENT_ID }}"
    api_key: "{{ USER_API_KEY }}"
    state: absent
```

## Return Values
- `msg` - Text that indicates the status of the module.
    - returned: always
    - type: str
    - sample: `mywebserv2 has been deleted`
- `server` - The sitehost server being actioned. Note that there is more information output on server creation and upgrade.
    - returned: On success
    - type: dict
    - elements:
        - `label` - User chosen label for the server.
            - returned: On success
            - type: str
            - sample: `mywebserver`
        - `name` - Unique system generated name for server.
            - returned: On success
            - type: str
            - sample: `mywebserv2`
        - `password` - Password for the root user.
            - returned: On success, and only returned during server creation.
            - type: str
            - sample: `Up8Da5oE60ns`
        - `state` - The state of the server after executing the command.
            - returned: On sucess
            - type: str
            - sample:
                - `On`
                - `Off`
                - `Reboot`
                - `Deleted`