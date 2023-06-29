# -*- coding: utf-8 -*-
# Copyright (c) 2021, René Moser <mail@renemoser.net>
# Simplified BSD License (see licenses/simplified_bsd.txt or https://opensource.org/licenses/BSD-2-Clause)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

import random
import time
from collections import OrderedDict
from ansible.errors import AnsibleError
from ansible.module_utils._text import to_text
from ansible.module_utils.basic import env_fallback
from ansible.module_utils.six.moves.urllib.parse import quote
from ansible.module_utils.urls import fetch_url, prepare_multipart

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

SH_USER_AGENT = "Ansible SiteHost"

def sitehost_argument_spec():
    return dict(
        api_endpoint=dict(
            type="str",
            fallback=(env_fallback, ["SH_API_ENDPOINT"]),
            default="https://api.staging.sitehost.nz/1.2",
        ),
        api_key=dict(
            type="str",
            fallback=(env_fallback, ["SH_API_KEY"]),
            no_log=True,
            required=True,
        ),
        api_client_id=dict(
            type="str",
            fallback=(env_fallback, ["SH_CLIENT_ID"]),
            required=True,
        ),
        api_timeout=dict(
            type="int",
            fallback=(env_fallback, ["SH_API_TIMEOUT"]),
            default=60,
        ),
        api_retries=dict(
            type="int",
            fallback=(env_fallback, ["SH_API_RETRIES"]),
            default=5,
        ),
        api_retry_max_delay=dict(
            type="int",
            fallback=(env_fallback, ["SH_API_RETRY_MAX_DELAY"]),
            default=12,
        ),
    )





class AnsibleSitehost:
    def __init__(
        self,
        module,
        namespace,
        resource_path,
        resource_result_key_singular,
        resource_result_key_plural=None,
        resource_key_name=None,
        resource_key_id="id",
        resource_get_details=False,
        resource_create_param_keys=None,
        resource_update_param_keys=None,
        resource_update_method="PATCH",
    ):

        self.module = module
        self.namespace = namespace

        # The API resource path e.g ssh_key
        self.resource_result_key_singular = resource_result_key_singular

        # The API result data key e.g ssh_keys
        self.resource_result_key_plural = resource_result_key_plural or "%ss" % resource_result_key_singular

        # The API resource path e.g /ssh-keys
        self.resource_path = resource_path

        # The API endpoint path e.g /provision.json
        self.resource_endpoint = ""

        # The name key of the resource, usually 'name'
        self.resource_key_name = resource_key_name

        # The name key of the resource, usually 'id'
        self.resource_key_id = resource_key_id

        # Some resources need an additional GET request to get all attributes
        self.resource_get_details = resource_get_details

        # List of params used to create the resource
        self.resource_create_param_keys = resource_create_param_keys or OrderedDict()

        # List of params used to update the resource
        self.resource_update_param_keys = resource_update_param_keys or OrderedDict()

        # Some resources have PUT, many have PATCH
        self.resource_update_method = resource_update_method

        self.result = {
            "changed": False,
            namespace: dict(),
            "diff": dict(before=dict(), after=dict()),
            "sitehost_api": {
                # "api_timeout": module.params["api_timeout"],
                # "api_retries": module.params["api_retries"],
                # "api_retry_max_delay": module.params["api_retry_max_delay"],
                "api_endpoint": module.params["api_endpoint"],
            },
        }

        self.headers = {
            # "Authorization": "Bearer %s" % self.module.params["api_key"],
            "User-Agent": SH_USER_AGENT,
            "Accept": "application/json",
        }

        # Check if the requests package is installed
        if not REQUESTS_AVAILABLE:
            self.module.fail_json(
            msg='requests is required for this module.  Please run "pip install requests"',
        )

        # Hook custom configurations
        self.configure()

    def configure(self):
        pass

    def transform_resource(self, resource):
        """
        Transforms (optional) the resource dict queried from the API
        """
        return resource

    def api_query(self, path, method="GET", data=None, query_params=None):
        """
        low level function that directly make http rquest to the sitehost api
        
            Parameters:
                path (str): should point to the api resource such as self.resource_path + apimethod
                method (str): defaults to "GET"
                data (dict): payload to use when using methods like POST
                query_params (dict): URL query string in dictionary form to use in methods like GET
            
            Return:
                a dictionary of the output of the http request

        """
        # auth
        query = "?apikey=%s&client_id=%s" % (self.module.params["api_key"], self.module.params["api_client_id"])
        if query_params:
            for k, v in query_params.items():
                query += "&%s=%s" % (to_text(k), quote(to_text(v)))

        path += query

        r = requests.request(method, headers=self.headers,
            url=self.module.params["api_endpoint"] + path,
            data=data
        )

        json_r = r.json()

        # Success with content
        if r.status_code in (200, 201, 202):
            if json_r['status'] == False:
                self.module.fail_json(**json_r)

            return self.module.from_json(to_text(r.text, errors="surrogate_or_strict"))

        # Success without content
        if r.status_code in (404, 204):
            return dict()

        self.module.fail_json(
            msg='Failure while calling the SiteHost API with %s for "%s". With message: %s' % (method, path,json_r["msg"]),
            #fetch_url_info=info,
        )

    def query_filter_list_by_name(
        self,
        path,
        key_name,
        result_key,
        param_key=None,
        key_id=None,
        query_params=None,
        get_details=False,
        fail_not_found=False,
        skip_transform=True,
    ):
        param_value = self.module.params.get(param_key or key_name)

        found = dict()
        for resource in self.query_list(path=path, result_key=result_key, query_params=query_params):
            if resource.get(key_name) == param_value:
                if found:
                    self.module.fail_json(msg="More than one record with name=%s found. " "Use multiple=yes if module supports it." % param_value)
                found = resource
        if found:
            if get_details:
                return self.query_by_id(resource_id=found[key_id], skip_transform=skip_transform)
            else:
                if skip_transform:
                    return found
                else:
                    return self.transform_resource(found)

        elif fail_not_found:
            self.module.fail_json(msg="No Resource %s with %s found: %s" % (path, key_name, param_value))

        return dict()

    def query_filter_list(self):
        # Returns a single dict representing the resource query by name
        return self.query_filter_list_by_name(
            key_name=self.resource_key_name,
            key_id=self.resource_key_id,
            get_details=self.resource_get_details,
            path=self.resource_path,
            result_key=self.resource_result_key_plural,
            skip_transform=False,
        )

    def query_by_id(self, resource_id=None, path=None, result_key=None, skip_transform=True):
        # Defaults
        path = path or self.resource_path
        result_key = result_key or self.resource_result_key_singular

        resource = self.api_query(path="%s%s" % (path, "/" + resource_id if resource_id else resource_id))
        if resource:
            if skip_transform:
                return resource[result_key]
            else:
                return self.transform_resource(resource[result_key])

        return dict()

    def query(self):
        # Returns a single dict representing the resource
        return self.query_filter_list()

    def query_list(self, path=None, result_key=None, query_params=None):
        # Defaults
        path = path or self.resource_path
        result_key = result_key or self.resource_result_key_plural

        resources = self.api_query(path=path, query_params=query_params)
        return resources[result_key] if resources else []

    def wait_for_job(self, job_id, state = "Completed"):
        """
        use it to pause execution of ansible task until the job is completed
        """
        for retry in range(0, 30):
            job_resource = self.api_query(
                path="/job/get.json",
                method="GET",
                query_params=dict(job_id=job_id, type="daemon")
            )

            job_status = job_resource.get("return")["state"]

            if job_status == state:
                break
            elif job_status == "Failed":
                self.module.fail_json(msg="Job %s failed" % (job_id))

            AnsibleSitehost._backoff(retry=retry)
        else:
            self.module.fail_json(msg="Wait for %s to become %s timed out" % (job_id, state))

    
    @staticmethod
    def _backoff(retry, retry_max_delay=12):
        """randomly pause the computation base on number of retries"""
        randomness = random.randint(0, 1000) / 1000.0
        delay = 2**retry + randomness
        if delay > retry_max_delay:
            delay = retry_max_delay + randomness
        time.sleep(delay)
    
    
    # def create_or_update(self):
    #     #resource = self.query()
    #     #if not resource:
    #     resource = self.create()
    #     #else:
    #         #resource = self.update(resource)
    #     return resource

    # def present(self):
    #     self.get_result(self.create_or_update())

    def is_diff(self, param, resource):
        value = self.module.params.get(param)
        if value is None:
            return False

        if param not in resource:
            self.module.fail_json(msg="Can not diff, key %s not found in resource" % param)

        if isinstance(value, list):
            for v in value:
                if v not in resource[param]:
                    return True
        elif resource[param] != value:
            return True

        return False

    def update(self, resource):
        data = dict()

        for param in self.resource_update_param_keys:
            if self.is_diff(param, resource):
                self.result["changed"] = True
                data[param] = self.module.params.get(param)

        if self.result["changed"]:
            self.result["diff"]["before"] = dict(**resource)
            self.result["diff"]["after"] = dict(**resource)
            self.result["diff"]["after"].update(data)

            if not self.module.check_mode:
                self.api_query(
                    path="%s/%s" % (self.resource_path, resource[self.resource_key_id]),
                    method=self.resource_update_method,
                    data=data,
                )
                resource = self.query_by_id(resource_id=resource[self.resource_key_id])
        return resource

    def absent(self):
        resource = self.query()
        if resource:
            self.result["changed"] = True

            self.result["diff"]["before"] = dict(**resource)
            self.result["diff"]["after"] = dict()

            if not self.module.check_mode:
                self.api_query(
                    path="%s/%s" % (self.resource_path, resource[self.resource_key_id]),
                    method="DELETE",
                )
        self.get_result(resource)

    def transform_result(self, resource):
        return resource

    def get_result(self, resource):
        self.result[self.namespace] = self.transform_result(resource)
        self.module.exit_json(**self.result)
