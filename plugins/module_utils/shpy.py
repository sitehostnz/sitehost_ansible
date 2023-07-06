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


    def api_query(self, path, method="GET", data=OrderedDict(), query_params=None):
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

        # if "provision" in path:
        #     raise Exception(["debug",data, path])

        # used for setting the api key and client id if they are not set
        data.setdefault("apikey",self.module.params["api_key"])
        data.setdefault("client_id",self.module.params["api_client_id"])
        # move the apikey to front of body followed by client_id (order matters)
        data.move_to_end("client_id", last=False)
        data.move_to_end("apikey", last=False)

        r = requests.request(method, headers=self.headers,
            url=self.module.params["api_endpoint"] + path,
            data=data
        )

        json_r = r.json()

        # Success with content
        if r.status_code in (200, 201, 202):
            if json_r['status'] == False:
                self.module.fail_json(**json_r, apiquery={"path":path, "body":data})

            return self.module.from_json(to_text(r.text, errors="surrogate_or_strict"))

        # Success without content
        if r.status_code in (404, 204):
            return dict()

        self.module.fail_json(
            msg='Failure while calling the SiteHost API with %s for "%s". With message: %s' % (method, path,json_r["msg"]),
            #fetch_url_info=info,
        )


    def wait_for_job(self, job_id, state = "Completed"):
        """
        use it to pause execution of ansible task until the job is completed

        :param job_id: the job id of the job to wait
        :param state: default to "Completed", the return state of when the job is consider done
        :returns: a dictionary of the job details
        """
        for retry in range(0, 30):
            job_resource = self.api_query(
                path="/job/get.json",
                method="GET",
                query_params=dict(job_id=job_id, type="daemon")
            )

            job_status = job_resource.get("return")["state"]

            if job_status == state:
                return job_resource["return"] # return information on job details when it succeded
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
    
    
    def get_result(self, resource):
        self.result[self.namespace] = self.transform_result(resource)
        self.module.exit_json(**self.result)
