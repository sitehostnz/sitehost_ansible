<p align="center">
    <a href="https://sitehost.nz" target="_blank">
        <img src=".github/sitehost-logo.svg" height="130">
    </a>
</p>

# SiteHost - Ansible Collection

Requirements
------------

- [Python](https://www.python.org/downloads/) 3.9+
- [Requests](https://pypi.org/project/requests/) 2.28.1
- [Ansible](https://pypi.org/project/ansible/) 7.1.0
- [Ansible Core](https://pypi.org/project/ansible-core/) 2.14.1 _included in ansible package_

## Setup

### Install dependencies

First you will need to install a compatible version of python as defined above. Then you can install the depency with `pip`. 

```bash
pip install ansible
pip install requests
```

### Install the Ansible Collection
You can use `ansible-galaxy` to install the SiteHost Ansible Collection:
```bash
ansible-galaxy collection install sitehost.cloud
```

## Usage
Once the Collection is installed, you can refrence it by its [Fully Qualified Collection Namespace (FQCN)](https://github.com/ansible-collections/overview#terminology): `sitehost.cloud.module_name`. 

In order to use this collection, the `SH_API_KEY` and `SH_CLIENT_ID` enviornment variable must be set to your SiteHost api key and client id respectively. Alternatetively, you can pass your api key and client id to the `api_key` and `api_client_id` option of the modules you are calling.

#### Example Playbook
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

## Modules
|Name| description|
|----|------------|
|[sitehost.cloud.server](./docs/server.md)| Manages SiteHost virtual server|
