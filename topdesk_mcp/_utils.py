import re
import requests
import urllib.parse
import logging

class utils:

    def __init__(self, topdesk_url, credpair):
        self._topdesk_url = topdesk_url
        self._credpair = credpair
        self._partial_content_container = []
        self._logger = logging.getLogger(__name__)

    def is_valid_uuid(self, uuid):
        result = re.match(r"^[0-9a-g]{8}-([0-9a-g]{4}-){3}[0-9a-g]{12}$", uuid)
        if result:
            self._logger.debug("Is a UUID: " + uuid)
        else:
            self._logger.debug("Not a UUID: " + uuid)
        return result
 
    def is_valid_email_addr(self, email_addr):
        result = re.match(r"(^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$)", email_addr)
        if result:
            self._logger.debug("Is an email address: " + email_addr)
        else:
            self._logger.debug("Not an email address: " + email_addr)
        return result

    def resolve_lookup_candidates(self, possible_candidates):
        if len(possible_candidates) == 1:
            self._logger.debug("Found one candidate: " + possible_candidates[0])
            return possible_candidates[0]
        elif len(possible_candidates) > 1:
            self._logger.warning("Found multiple candidates: " + "; ".join(possible_candidates) + ". Returning first one.")
            return possible_candidates[0]
        else:
            self._logger.debug("No candidates found.")
            return None

    def request_topdesk(self, uri, archived=None, page_size=None, query=None, custom_uri=None, extended_uri=None):
        """
        Build and send a GET request to the TOPdesk API, handling query parameters robustly.
        """
        headers = {
            'Authorization': f"Basic {self._credpair}",
            "Accept": 'application/json'
        }
        base_url = self._topdesk_url
        params = {}
        # Handle custom_uri as a dict of query params
        if custom_uri:
            params.update(custom_uri)
        if page_size:
            params['page_size'] = page_size
        if extended_uri:
            params.update(extended_uri)
        if archived is not None:
            params['query'] = f"archived=={archived}"
        if query:
            # If 'query' already in params, append with semicolon
            if 'query' in params:
                params['query'] += f";{query}"
            else:
                params['query'] = query
        # Build the full URL
        if params:
            query_string = urllib.parse.urlencode(params, quote_via=urllib.parse.quote_plus)
            if '?' in uri:
                url = f"{base_url}{uri}&{query_string}"
            else:
                url = f"{base_url}{uri}?{query_string}"
        else:
            url = f"{base_url}{uri}"
        return requests.get(url, headers=headers)

    def handle_topdesk_response(self, response):
        """
        Handle a TOPdesk API response, including partial content and error handling.
        """
        self._logger.debug("Response from TopDesk API: HTTP Status Code {}: {}".format(response.status_code, response.text))

        if response.status_code >= 200 and response.status_code < 300:
            return self._handle_success_response(response)
        elif response.status_code >= 400 and response.status_code < 500:
            return self._handle_client_error(response)
        elif response.status_code >= 500 and response.status_code < 600:
            return self._handle_server_error(response)
        else:
            return self._handle_other_error(response)
        
    def _handle_success_response(self, response):
        """
        Handle a successful response from the TOPdesk API.
        """
        # Success (OK or Created)
        if response.status_code in (200, 201):
            if not self._partial_content_container:
                if not response.text:
                    return "Success"
                return response.json()
            else:
                self._partial_content_container += response.json()
                result = self._partial_content_container
                self._partial_content_container = []
                return result
        # No Content
        if response.status_code == 204:
            self._logger.debug("status_code 204, message: No content")
            return "Success"
        # Partial Content (pagination)
        if response.status_code == 206:
            self._handle_partial_content(response)
            
    def _handle_partial_content(self, response):
        self._partial_content_container += response.json()
        # Try to extract page_size and start from the URL
        page_size_match = re.search(r'page_size=(\d+)', response.url)
        page_size = int(page_size_match.group(1)) if page_size_match else 0
        start_match = re.search(r'start=(\d+)', response.url)
        current_start = int(start_match.group(1)) if start_match else 0
        new_start = current_start + page_size if page_size else 0
        # Update or add start param
        if 'start=' in response.url:
            next_url = re.sub(r'start=\d+', f'start={new_start}', response.url)
        elif page_size:
            next_url = re.sub(r'(page_size=\d+)', f"\\1&start={page_size}", response.url)
        else:
            next_url = response.url
        # Remove base url for recursive call
        next_url = next_url.replace(self._topdesk_url, "")
        return self.handle_topdesk_response(self.request_topdesk(next_url))
    
    def _handle_client_error(self, response):
        """
        Handle client errors (4xx) from the TOPdesk API.
        """
        if response.status_code == 400:
            error = "Bad Request: The request was invalid or cannot be served."
        elif response.status_code == 401:
            error = "Unauthorized: Authentication credentials were missing or incorrect."
        elif response.status_code == 403:
            error = "Forbidden: The request is understood, but it has been refused or access is not allowed."
        elif response.status_code == 404:
            error = "Not Found: The URI requested is invalid or the resource does not exist."
        elif response.status_code == 409:
            error = "Conflict: The request could not be completed due to a conflict with the current state of the resource."
        else:
            error = f"Client Error {response.status_code}: {response.text}"
        
        self._logger.error(error)
        return error
    
    def _handle_server_error(self, response):
        """
        Handle server errors (5xx) from the TOPdesk API.
        """
        error = f"Server Error {response.status_code}: {response.text}"
        self._logger.error(error)
        return error
    
    def _handle_other_error(self, response):
        # General failure
        try:
            error_json = response.json()
        except Exception:
            error_json = {}
        status_code = response.status_code
        if isinstance(error_json, dict) and 'errors' in error_json:
            error = f"HTTP Status Code {status_code}: {error_json['errors'][0]['errorMessage']}"
            self._logger.error(error)
            return error
        elif isinstance(error_json, list) and error_json and 'message' in error_json[0]:
            error = f"HTTP Status Code {status_code}: {error_json[0]['message']}"
            self._logger.error(error)
            return error
        else:
            error = f"HTTP Status Code {status_code}: {response.text}"
            self._logger.error(error)
            return error
        
    def post_to_topdesk(self, uri, json_body):
        headers = {'Authorization':"Basic {}".format(self._credpair), "Accept":'application/json', \
            'Content-type': 'application/json'}
        return requests.post(self._topdesk_url + uri, headers=headers, json=json_body)

    def put_to_topdesk(self, uri, json_body):
        headers = {'Authorization':"Basic {}".format(self._credpair), "Accept":'application/json', \
            'Content-type': 'application/json'}
        return requests.put(self._topdesk_url + uri, headers=headers, json=json_body)
    
    def patch_to_topdesk(self, uri, json_body):
        headers = {'Authorization':"Basic {}".format(self._credpair), "Accept":'application/json', \
            'Content-type': 'application/json'}
        return requests.patch(self._topdesk_url + uri, headers=headers, json=json_body)

    def delete_from_topdesk(self, uri, json_body):
        headers = {'Authorization':"Basic {}".format(self._credpair), "Accept":'application/json', \
            'Content-type': 'application/json'}
        return requests.delete(self._topdesk_url + uri, headers=headers, json=json_body)

    def add_id_list(self, id_list):
        param = []
        for item in id_list:
            param.append({'id': item})
        return param

    def add_id_jsonbody(self, **kwargs):
        request_body = {}
        
        # args = posible caller
        if 'caller' in kwargs:            
            if self.is_valid_email_addr(kwargs['caller']):
                caller_type = "email"
            elif self.is_valid_uuid(kwargs['caller']):
                caller_type = "id"
            else:
                caller_type = "dynamicName"
            request_body['callerLookup'] = { caller_type: kwargs['caller']}

        for key in kwargs:
            if self.is_valid_uuid(str(kwargs[key])):
                request_body[key] = { 'id' : kwargs[key] }
            else:
                if key == 'caller': 
                    continue
                request_body[key] = kwargs[key]
        return request_body
