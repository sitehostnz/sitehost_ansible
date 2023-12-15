from __future__ import absolute_import, division, print_function

__metaclass__ = type

import traceback
import random
import time
from collections import OrderedDict
from ansible.module_utils._text import to_text
from ansible.module_utils.basic import env_fallback, missing_required_lib
from ansible.module_utils.six.moves.urllib.parse import quote


HTTP_INTERNAL_SERVER_ERROR_STATUS_CODE = 500

try:
    import requests

    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    LIB_REQ_ERR = traceback.format_exc()

SH_USER_AGENT = "Ansible SiteHost"


class SitehostAPI:
    def __init__(self, module, api_key, api_client_id):
        self.module = module
        self.api_key = api_key
        self.api_client_id = api_client_id

        self.headers = {
            "User-Agent": SH_USER_AGENT,
            "Accept": "application/json",
        }

        # Check if the requests package is installed
        if not REQUESTS_AVAILABLE:
            self.module.fail_json(
                msg=missing_required_lib(
                    library="requests",
                    url="https://pypi.org/project/requests/",
                    reason="because it is required for accessing the sitehost api",
                ),
                exception=LIB_REQ_ERR,
            )

    def api_query(
        self,
        path,
        method="GET",
        data=OrderedDict(),
        query_params=None,
        skip_status_check=False,
    ):
        """
        low level function that directly make http rquest to the sitehost api

            Parameters:
                path (str): should point to the api resource such as "/server/provision.json"
                method (str): defaults to "GET"
                data (dict): payload to use when using methods like POST
                query_params (dict): URL query string in dictionary form to use in methods like GET
                skip_status_check (bool): Prevents module interruption when
                    'status==False'. Set to True in cases where 'status==False' is a
                    normal operational outcome.

            Return:
                a dictionary of the output of the http request

        """
        # auth
        query = f"?apikey={self.api_key}&client_id={self.api_client_id}"
        if query_params:
            for k, v in query_params.items():
                query += f"&{to_text(k)}={quote(to_text(v))}"

        path += query

        # used for setting the api key and client id if they are not set
        data.setdefault("apikey", self.api_key)
        data.setdefault("client_id", self.api_client_id)
        # move the apikey to front of body followed by client_id (order matters)
        data.move_to_end("client_id", last=False)
        data.move_to_end("apikey", last=False)

        r = requests.request(
            method,
            headers=self.headers,
            url=self.module.params["api_endpoint"] + path,
            data=data,
        )

        if r.status_code == HTTP_INTERNAL_SERVER_ERROR_STATUS_CODE:
            self.module.fail_json(
                msg=(
                    "An unexpected error has occured while calling SiteHost API,"
                    "please contact SiteHost support."
                ),
                path=path,
                POST_data=data,
                GET_params=query_params,
            )

        json_r = r.json()

        # generally if the return status is false, there is an error
        # interupt and stop the module execution unless `skip_status_check` is True
        if json_r.get("status") is False and not skip_status_check:
            self.module.fail_json(
                msg=(
                    f"An error has occured while calling the SiteHost API"
                    f' With message: "{json_r["msg"]}".'
                ),
                error_code=r.status_code,
            )

        # Success with content
        if r.status_code in (200, 201, 202):
            return self.module.from_json(to_text(r.text, errors="surrogate_or_strict"))

        # Success without content
        if r.status_code in (404, 204):
            return dict()

        self.module.fail_json(
            msg=(
                f'Failure while calling the SiteHost API with {method} for "{path}".'
                f' With message: {json_r["msg"]}'
            ),
            error_code=r.status_code,
        )

    def wait_for_job(self, job_id, job_type="daemon", state="Completed"):
        """
        use it to pause execution of ansible task until the job is completed

        :param job_id: the job id of the job to wait
        :param job_type: Specifies the scheduler type: "scheduler" for cloud containers,
                        or "daemon" for everything else.
        :param state: default to "Completed", the return state of when the job is consider done
        :returns: a dictionary of the job details
        """
        for retry in range(0, 30):
            job_resource = self.api_query(
                path="/job/get.json",
                method="GET",
                query_params=dict(job_id=job_id, type=job_type),
            )

            job_status = job_resource.get("return")["state"]

            # return information on job details when it succeded
            if job_status == state:
                return job_resource["return"]
            elif job_status == "Failed":
                self.module.fail_json(
                    msg=f"Job {job_id} failed", job_result=job_resource
                )

            SitehostAPI._backoff(retry=retry)
        else:
            self.module.fail_json(
                msg=f"Wait for {job_id} to become {state} timed out",
                job_result=job_resource,
            )

    @staticmethod
    def _backoff(retry, retry_max_delay=60):
        """
        Pause the computation for some time, based on the number of retries
        retries are kept track by the parent wait_for_job() method.

        Basically with every iteration of retry, the function will wait alittle longer
        until it waits for a max of retry_max_delay seconds.

        :param retry: The current iteration of the delay method
        :param retry_max_delay: The maximum allowed time to wait per iteration
        """
        randomness = random.randint(0, 1000) / 1000.0
        delay = 2**retry + randomness
        if delay > retry_max_delay:
            delay = retry_max_delay + randomness
        time.sleep(delay)

    @staticmethod
    def sitehost_argument_spec():
        return dict(
            api_endpoint=dict(
                type="str",
                fallback=(env_fallback, ["SH_API_ENDPOINT"]),
                default="https://api.sitehost.nz/1.2",
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
        )
