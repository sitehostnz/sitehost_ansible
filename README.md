<p align="center">
    <a href="https://sitehost.nz" target="_blank">
        <img src=".github/sitehost-logo.svg" height="130">
    </a>
</p>

## SiteHost - Ansible Collection

Requirements
------------

- [Python](https://www.python.org/downloads/) 3.9+
- [Requests](https://pypi.org/project/requests/) 2.28.1
- [Ansible](https://pypi.org/project/ansible/) 7.1.0
- [Ansible Core](https://pypi.org/project/ansible-core/) 2.14.1 _included in ansible package_

### Setup

You need to setup the email and password in your environment variables.

```bash
export SH_API_KEY='********'
export SH_CLIENT_ID='********'
```

### Install dependencies

```bash
pip install ansible
pip install requests
```

> **_NOTE:_**  We suggest install `pyenv` and create a virtualenv to test this project, you can follow our [internal guide](https://gitlab.sitehost.co.nz/ops/operations-internal/-/issues/494#note_77555).

### Build and Install Ansible Collection

Clone this repo in your local machine, then you can build and install the ansible collection. Follow these steps.

```sh
git clone https://gitlab.sitehost.co.nz/gonzalo/ansible-collection-sitehost
cd ansible-collection-sitehost
ansible-galaxy collection build --force && ansible-galaxy collection install sitehost-cloud-1.0.0.tar.gz -vvv --force
```

### Test Ansible Collection

You need to create a new yaml file `test.yml` with the playbook, here an example.
```yaml
---
- hosts: localhost
  gather_facts: False

  tasks:
    - name: Create a VPS with 1.5G RAM OS Ubuntu 20.04
      sitehost.cloud.server:
        label: ansiblet1
        location: AKLCITY
        product_code: XENLIT
        image: ubuntu-focal.amd64
```
> **_NOTE:_**  You can see the location, product_code and images list in our [KB](https://kb.sitehost.nz/developers/api).

### Running the playbook

You can test the playbook with the following command.

```bash
ansible-playbook test.yml
```

If you need more details you can add `-vvv`.

```bash
ansible-playbook test.yml -vvv
```