<p align="center">
    <a href="https://sitehost.nz" target="_blank">
        <img src="https://raw.githubusercontent.com/sitehostnz/sitehost_ansible/main/.github/sitehost-logo.svg" alt="SiteHost"  height="130">
    </a>
</p>

# sitehost.cloud.stack
Manages SiteHost Cloud Containers. Make sure to check out our [developer KB article](https://kb.sitehost.nz/developers) for more information on our API. Please ensure that the `Servers & Cloud Containers: Cloud` and `Servers & Cloud Containers: Job` privilege is enabled for your SiteHost API key.

- [parameters](#parameter)
- [examples](#examples)
- [return](#return-values)

## Parameter
| Field     | Type | Required | Description                                                                  |
|-----------|------|----------|------------------------------------------------------------------------------|
| `state` | <center>`str`</center> | <center>Optional **(Default: present)**</center> | The desired state of the Cloud Container.  **(Choices: `present`, `absent`, `started`,`stopped`, `restarted`)** |
| `server` | <center>`str`</center> | <center>**Required**</center> |The Cloud Container server to operate on.  |
| `name` | <center>`str`</center> |<center>**Required**</center> | A unique Hash assigned to the server. [Generate](https://docs.sitehost.nz/api/v1.2/?path=/cloud/stack/generate_name&action=GET) one with the API before hand before using it.|
| `label` | <center>`str`</center> | <center>Optional</center> | User chosen label of the Container. The label format must be a valid FQDN. *eg. mycontainer.co.nz* |
| `docker_compose` | <center>`str`</center> | <center>Optional</center> | The docker_compose file that needs to be set when creating a server. |
| `api_key` | <center>`str`</center> | <center>**Required**</center> | Your SiteHost API key [generated from CP](https://kb.sitehost.nz/developers/api#creating-an-api-key). |
| `api_client_id` | <center>`int`</center> | <center>**Required**</center> | The client ID of your SiteHost account. |

### `docker_compose` parameter
Our Cloud Containers are powered by Docker. As such, users will be required to provide a [docker-compose file](https://docs.docker.com/compose/compose-file/03-compose-file/) as a string when provisioning Cloud Containers.  

The following is the general format of the `docker_compose` file:
```
version: '2.1'
    services:
        {{CLOUD_CONTAINER_NAME}}:
            container_name: {{CLOUD_CONTAINER_NAME}}
            environment:
                - 'VIRTUAL_HOST={{CLOUD_CONTAINER_LABEL}},www.{{CLOUD_CONTAINER_LABEL}}'
                - CERT_NAME={{CLOUD_CONTAINER_LABEL}}
            expose:
                - 80/tcp
            image: {{CONTAINER_IMAGE}}
            labels:
                - 'nz.sitehost.container.website.vhosts={{CLOUD_CONTAINER_LABEL}},www.{{CLOUD_CONTAINER_LABEL}}'
                - nz.sitehost.container.image_update=True
                - nz.sitehost.container.label={{CLOUD_CONTAINER_LABEL}}
                - nz.sitehost.container.type={{CONTAINER_TYPE}}
                - nz.sitehost.container.monitored=True
                - nz.sitehost.container.backup_disable=False
            restart: unless-stopped
            volumes:
                - '/data/docker0/{{CONTAINER_TYPE}}/{{CLOUD_CONTAINER_NAME}}/crontabs:/cron:ro'
                - '/data/docker0/{{CONTAINER_TYPE}}/{{CLOUD_CONTAINER_NAME}}/application:/container/application:rw'
                - '/data/docker0/{{CONTAINER_TYPE}}/{{CLOUD_CONTAINER_NAME}}/config:/container/config:ro'
                - '/data/docker0/{{CONTAINER_TYPE}}/{{CLOUD_CONTAINER_NAME}}/logs:/container/logs:rw'
    networks:
        default:
            external:
                name: infra_default
```
Where `{{CLOUD_CONTAINER_NAME}}` must match `name` and `{{CLOUD_CONTAINER_LABEL}}` must match `label`.

The provided template should serve only as a reference. We strongly recommend obtaining a copy of `docker_compose` from an existing container using our [API](https://docs.sitehost.nz/api/v1.2/?path=/cloud/stack/get&action=GET). Once you have it, replace the `name` and `label` values in the `docker_compose` with your own. Doing this ensures that the new container uses the correct `docker_compose` settings for the selected image.

You can find a `docker_compose` for the Apache + PHP 8.2 image in the [examples](#examples) section below.

## Examples

- Create a Cloud Container running apache + php 8.2
> Note: In the `docker_compose` paramter, the bar (`|`) symbol is used to denote multi-line string input.
```
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
```

- Delete a Cloud Container
```
- name: delete a container
  sitehost.cloud.stack:
    server: ch-mycloudse
    name: ccb7a31da52e5b47
    api_client_id: "{{ CLIENT_ID }}"
    api_key: "{{ USER_API_KEY }}"
    state: absent
```
- Powering up a Cloud Container
```
- name: start container
  sitehost.cloud.stack:
    server: ch-mycloudse
    name: ccb7a31da52e5b47
    api_client_id: "{{ CLIENT_ID }}"
    api_key: "{{ USER_API_KEY }}"
    state: started
```

## Return

- msg:
    - description: A short messages showing the state of the module execution.
    - type: str
    - returned: always
    - sample: 'Container ccb7a31da52e5b47 created'
- stack:
    - description: The Cloud Container status.
    - type: dict
    - returned: success
    - sample: 
    ```
    {
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
    ```