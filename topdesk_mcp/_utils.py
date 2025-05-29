import re
import requests
import urllib.parse
import logging
import base64
import os
from markitdown import MarkItDown  # Add this import

class utils:

    def __init__(self, topdesk_url, credpair):
        self._topdesk_url = topdesk_url
        self._credpair = credpair
        self._partial_content_container = []
        self._logger = logging.getLogger(__name__)
        # Set SSL verification based on environment variable
        self._ssl_verify = os.getenv('SSL_VERIFY', 'true').lower() != 'false'
        if not self._ssl_verify:
            # Disable SSL warnings when verification is disabled
            import urllib3
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
            self._logger.warning("SSL verification is disabled")

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
            self._logger.debug("Found one candidate: " + str(possible_candidates[0]))
            return possible_candidates[0]
        elif len(possible_candidates) > 1:
            self._logger.warning("Found multiple candidates: " + "; ".join(str(candidate) for candidate in possible_candidates) + ". Returning first one.")
            return possible_candidates[0]
        else:
            self._logger.debug("No candidates found.")
            return []

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
        return requests.get(url, headers=headers, verify=self._ssl_verify)

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
                # Check if response is a file download (non-JSON content)
                content_type = response.headers.get('Content-Type', '')
                if content_type and 'application/json' not in content_type.lower():
                    self._logger.debug(f"Received file download with Content-Type: {content_type}")
                    # Return base64 encoding of binary content
                    return {
                        'content_type': content_type,
                        'filename': self._get_filename_from_headers(response.headers),
                        'base64_data': base64.b64encode(response.content).decode('utf-8')
                    }
                
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

    def _get_filename_from_headers(self, headers):
        """
        Extract filename from Content-Disposition header if present.
        """
        content_disposition = headers.get('Content-Disposition', '')
        filename_match = re.search(r'filename="?([^";]+)', content_disposition)
        if filename_match:
            return filename_match.group(1)
        return 'downloaded_file'

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
        return requests.post(self._topdesk_url + uri, headers=headers, json=json_body, verify=self._ssl_verify)

    def put_to_topdesk(self, uri, json_body):
        headers = {'Authorization':"Basic {}".format(self._credpair), "Accept":'application/json', \
            'Content-type': 'application/json'}
        return requests.put(self._topdesk_url + uri, headers=headers, json=json_body, verify=self._ssl_verify)
    
    def patch_to_topdesk(self, uri, json_body):
        headers = {'Authorization':"Basic {}".format(self._credpair), "Accept":'application/json', \
            'Content-type': 'application/json'}
        return requests.patch(self._topdesk_url + uri, headers=headers, json=json_body, verify=self._ssl_verify)

    def delete_from_topdesk(self, uri, json_body):
        headers = {'Authorization':"Basic {}".format(self._credpair), "Accept":'application/json', \
            'Content-type': 'application/json'}
        return requests.delete(self._topdesk_url + uri, headers=headers, json=json_body, verify=self._ssl_verify)

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

    def convert_with_docling(self, file_path, file_name, docling_address):
        """
        Convert a document to markdown using Docling API with file type-specific parameters
        
        Args:
            file_path: Path to the temporary file
            file_name: Original file name
            docling_address: URL of the Docling API
            
        Returns:
            dict: A structured dictionary containing:
                - extracted_text: The document content converted to markdown text
                - description: Empty string or additional context about the document
                - __comment: Processing information or error message if conversion failed
        """
        logger = logging.getLogger(__name__)
        try:
            logger.debug(f"Using Docling at {docling_address} for document conversion")
            
            # Prepare API endpoint
            endpoint = f"{docling_address}/v1alpha/convert/file"
            
            # Setup authentication
            headers = {'accept': 'application/json'}
            auth = None
            
            # Check for API key auth (preferred if available)
            api_key = os.getenv('DOCLING_API_KEY')
            if api_key:
                logger.debug("Using API key authentication for Docling")
                headers['Authorization'] = f"Bearer {api_key}"
            
            # Fall back to username/password auth if API key not available
            elif os.getenv('DOCLING_USERNAME') and os.getenv('DOCLING_PASSWORD'):
                logger.debug("Using username/password authentication for Docling")
                username = os.getenv('DOCLING_USERNAME')
                password = os.getenv('DOCLING_PASSWORD')
                auth = requests.auth.HTTPBasicAuth(username, password)
            
            # Determine file type and parameters based on extension
            _, extension = os.path.splitext(file_name)
            extension = extension.lower().lstrip('.')
            
            # Set up common parameters for all file types
            data = {
                'do_code_enrichment': 'false',
                'ocr_engine': 'easyocr',
                'images_scale': '2',
                'pdf_backend': 'dlparse_v4',
                'do_picture_description': 'false',
                'force_ocr': 'false',
                'image_export_mode': 'placeholder',
                'do_ocr': 'true',
                'do_table_structure': 'true',
                'include_images': 'false',
                'do_formula_enrichment': 'false',
                'table_mode': 'fast',
                'abort_on_error': 'false',
                'to_formats': 'md',
                'return_as_file': 'false',
                'do_picture_classification': 'false'
            }
            
            # Determine from_formats and content type based on file extension
            image_extensions = ['png', 'jpg', 'jpeg', 'gif', 'bmp', 'tiff', 'webp']
            
            if extension == 'pdf':
                data['from_formats'] = 'pdf'
                content_type = 'application/pdf'
            elif extension in image_extensions:
                data['from_formats'] = 'image'
                content_type = f'image/{extension}'
            elif extension == 'docx':
                data['from_formats'] = 'docx'
                content_type = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
            elif extension == 'pptx':
                data['from_formats'] = 'pptx'
                content_type = 'application/vnd.openxmlformats-officedocument.presentationml.presentation'
            elif extension == 'xlsx':
                data['from_formats'] = 'xlsx'
                content_type = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            elif extension == 'html' or extension == 'htm':
                data['from_formats'] = 'html'
                content_type = 'text/html'
            elif extension == 'md':
                data['from_formats'] = 'md'
                content_type = 'text/markdown'
            elif extension == 'csv':
                data['from_formats'] = 'csv'
                content_type = 'text/csv'
            else:
                # Default to HTML handling if extension not recognized
                logger.warning(f"Unrecognized file extension: {extension}, defaulting to generic handling for HTML")
                data['from_formats'] = 'html'  # Default, may need adjustment
                content_type = 'application/html'
            
            logger.debug(f"Processing file as {data['from_formats']} with content type {content_type}")
            
            # Send the file to the Docling API with appropriate parameters
            with open(file_path, 'rb') as document_file:
                files = {'files': (file_name, document_file, content_type)}
                response = requests.post(endpoint, files=files, data=data, headers=headers, auth=auth, verify=self._ssl_verify)
            
            if response.status_code == 200:
                # Process Docling response
                docling_response = response.json()
                md_content = docling_response['document']['md_content']
                
                # Return in unified structured format
                return {
                    "extracted_text": md_content,
                    "description": "",
                    "__comment": f"Document converted from {extension.upper()} using Docling API"
                }
            else:
                logger.warning(f"Docling API returned status {response.status_code}: {response.text}")
                return {
                    "extracted_text": "",
                    "description": "",
                    "__comment": f"Docling API returned status {response.status_code}: {response.text}"
                }
        except Exception as e:
            logger.warning(f"Error using Docling API: {e}")
            return {
                "extracted_text": "",
                "description": "",
                "__comment": f"Error processing attachment with Docling: {e}"
            }

    def convert_with_openai(self, file_path, file_name, openai_endpoint):
        """
        Convert a document to markdown using OpenAI API
        
        Args:
            file_path: Path to the temporary file
            file_name: Original file name
            openai_endpoint: URL of the OpenAI API endpoint
            
        Returns:
            dict: A structured dictionary containing:
                - extracted_text: The document content converted to markdown text
                - description: Document summary or additional context about the content
                - __comment: Processing information or error message if conversion failed
        """
        logger = logging.getLogger(__name__)
        try:
            logger.debug(f"Using OpenAI endpoint at {openai_endpoint} for document conversion")
            
            # Check for API key
            api_key = os.getenv('OPENAI_API_KEY')
            if not api_key:
                logger.error("OPENAI_API_KEY not found in environment variables")
                return {
                    "extracted_text": "",
                    "description": "",
                    "__comment": "Error: OPENAI_API_KEY not found in environment variables"
                }
            
            # Determine file type based on extension
            _, extension = os.path.splitext(file_name)
            extension = extension.lower().lstrip('.')
            
            # Define supported file types
            image_extensions = ['png', 'jpg', 'jpeg', 'gif', 'webp', 'bmp', 'tiff']
            document_extensions = ['pdf', 'docx', 'xlsx', 'xls', 'csv', 'html', 'htm', 'md', 'txt']
            
            if extension in image_extensions:
                return self._convert_image_with_openai(file_path, file_name, extension, openai_endpoint, api_key)
            elif extension in document_extensions:
                return self._convert_document_with_openai(file_path, file_name, extension, openai_endpoint, api_key)
            else:
                logger.warning(f"Unsupported file extension: {extension}")
                return {
                    "extracted_text": "",
                    "description": "",
                    "__comment": f"Unsupported file extension: {extension}"
                }
        except Exception as e:
            logger.error(f"Error using OpenAI API: {e}")
            return {
                "extracted_text": "",
                "description": "",
                "__comment": f"Error processing attachment with OpenAI: {e}"
            }
    
    def _convert_image_with_openai(self, file_path, file_name, extension, openai_endpoint, api_key):
        """
        Convert image files using OpenAI vision API
        
        Args:
            file_path: Path to the temporary file
            file_name: Original file name
            extension: File extension of the image
            openai_endpoint: OpenAI API endpoint URL
            api_key: OpenAI API key
            
        Returns:
            dict: A structured dictionary containing:
                - extracted_text: Any text extracted from the image, formatted as markdown
                - description: Visual description of the image content
                - __comment: Processing information or error message if conversion failed
        """
        logger = logging.getLogger(__name__)
        
        # Read and encode the file as base64
        with open(file_path, 'rb') as file:
            file_content = file.read()
            base64_content = base64.b64encode(file_content).decode('utf-8')
        
        # Map extensions to MIME types
        mime_types = {
            'png': 'image/png',
            'jpg': 'image/jpeg',
            'jpeg': 'image/jpeg',
            'gif': 'image/gif',
            'webp': 'image/webp',
            'bmp': 'image/bmp',
            'tiff': 'image/tiff'
        }
        
        media_type = mime_types.get(extension, 'image/jpeg')
        logger.debug(f"Processing image file as {media_type}")
        
        # Get model name from environment or use default
        model_name = os.getenv('OPENAI_MODEL_NAME', 'gpt-4.1')
        
        # Prepare the API request for vision
        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }
        
        system_prompt = """You are an expert at extracting text from images and describing visual content. 
        Please analyze the provided image and:
        1. Extract ALL visible text from the image and format it as clean Markdown
        2. Provide a detailed description of the image content, layout, and visual elements
        
        Return your response as a JSON object with the following structure:
        {
            "extracted_text": "All text from the image formatted as Markdown",
            "description": "Detailed description of the image content and visual elements"
        }"""
        
        payload = {
            "model": model_name,
            "messages": [
                {
                    "role": "system",
                    "content": system_prompt
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": f"Please extract all text and describe this image: {file_name}"
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{media_type};base64,{base64_content}",
                                "detail": "high"
                            }
                        }
                    ]
                }
            ],
            "max_tokens": 4000,
            "temperature": 0.1
        }
        
        return self._make_openai_request(openai_endpoint, headers, payload)
    
    def _convert_document_with_openai(self, file_path, file_name, extension, openai_endpoint, api_key):
        """
        Convert document files using OpenAI by sending the raw file
        
        Args:
            file_path: Path to the temporary file
            file_name: Original file name
            extension: File extension of the document
            openai_endpoint: OpenAI API endpoint URL
            api_key: OpenAI API key
            
        Returns:
            dict: A structured dictionary containing:
                - extracted_text: Document content extracted and formatted as markdown
                - description: Document summary or context about the content
                - __comment: Processing information or error message if conversion failed
        """
        logger = logging.getLogger(__name__)
        
        # Read and encode the file as base64
        with open(file_path, 'rb') as file:
            file_content = file.read()
            base64_content = base64.b64encode(file_content).decode('utf-8')
        
        # Check file size (OpenAI has limits)
        file_size_mb = len(file_content) / (1024 * 1024)
        if file_size_mb > 20:  # Conservative limit
            logger.warning(f"File {file_name} is {file_size_mb:.1f}MB, which may be too large for OpenAI API")
            return {
                "extracted_text": "",
                "description": "",
                "__comment": f"File {file_name} is too large for OpenAI API (size: {file_size_mb:.1f}MB)"
            }
        
        # Get model name from environment or use default
        model_name = os.getenv('OPENAI_MODEL_NAME', 'gpt-4.1')
        
        # Prepare the API request
        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }
        
        # Different handling based on file type
        if extension == 'pdf':
            system_prompt = """You are an expert at extracting and structuring content from PDF documents.
            I will provide you with a PDF file in base64 format. Please:
            1. Extract ALL text content from the PDF and format it as clean, well-structured Markdown
            2. Preserve the document structure (headings, lists, tables, etc.)
            3. Provide a summary description of the document's content, structure, and key information
            
            Return your response as a JSON object with the following structure:
            {
                "extracted_text": "All document content formatted as clean, well-structured Markdown",
                "description": "Summary of the document's content, structure, and key information"
            }"""
            
            user_content = f"Please extract all content from this PDF file: {file_name}\n\nBase64 content: {base64_content[:1000]}..."
            
        elif extension in ['docx', 'xlsx', 'xls']:
            system_prompt = f"""You are an expert at extracting and structuring content from Microsoft Office documents.
            I will provide you with a {extension.upper()} file in base64 format. Please:
            1. Extract ALL text content and data from the document and format it as clean Markdown
            2. For spreadsheets, convert tables to Markdown table format
            3. Preserve document structure and formatting where possible
            4. Provide a summary description of the document's content and structure
            
            Return your response as a JSON object with the following structure:
            {{
                "extracted_text": "All document content formatted as clean Markdown",
                "description": "Summary of the document's content and structure"
            }}"""
            
            user_content = f"Please extract all content from this {extension.upper()} file: {file_name}\n\nBase64 content: {base64_content[:1000]}..."
            
        elif extension == 'csv':
            # For CSV, we can decode and send the text content directly
            try:
                csv_content = file_content.decode('utf-8')
                system_prompt = """You are an expert at analyzing and formatting CSV data.
                Please analyze the provided CSV content and:
                1. Convert the CSV data into a well-formatted Markdown table
                2. Provide a summary of the data structure, columns, and key insights
                
                Return your response as a JSON object with the following structure:
                {
                    "extracted_text": "CSV data formatted as a clean Markdown table",
                    "description": "Summary of the data structure, columns, and key insights"
                }"""
                
                user_content = f"Please analyze and format this CSV file: {file_name}\n\nCSV content:\n{csv_content}"
                
            except UnicodeDecodeError:
                logger.error(f"Could not decode CSV file {file_name} as UTF-8")
                return {
                    "extracted_text": "",
                    "description": "",
                    "__comment": f"Error decoding CSV file {file_name} as UTF-8"
                }
                
        elif extension in ['html', 'htm', 'md', 'txt']:
            # For text-based files, decode and send content directly
            try:
                text_content = file_content.decode('utf-8')
                system_prompt = f"""You are an expert at analyzing and cleaning {extension.upper()} content.
                Please analyze the provided {extension.upper()} content and:
                1. Clean and reformat the content as well-structured Markdown
                2. Remove any formatting artifacts or unwanted elements
                3. Provide a summary of the content and structure
                
                Return your response as a JSON object with the following structure:
                {{
                    "extracted_text": "Content cleaned and formatted as Markdown",
                    "description": "Summary of the content and structure"
                }}"""
                
                # Truncate if too long
                max_chars = 50000
                if len(text_content) > max_chars:
                    text_content = text_content[:max_chars] + "\n\n[Content truncated due to length...]"
                
                user_content = f"Please clean and format this {extension.upper()} file: {file_name}\n\nContent:\n{text_content}"
                
            except UnicodeDecodeError:
                logger.error(f"Could not decode {extension} file {file_name} as UTF-8")
                return {
                    "extracted_text": "",
                    "description": "",
                    "__comment": f"Error decoding {extension} file {file_name} as UTF-8"
                }
        else:
            logger.warning(f"Unsupported document type: {extension}")
            return {
                "extracted_text": "",
                "description": "",
                "__comment": f"Unsupported document type: {extension}"
            }
        
        payload = {
            "model": model_name,
            "messages": [
                {
                    "role": "system",
                    "content": system_prompt
                },
                {
                    "role": "user",
                    "content": user_content
                }
            ],
            "max_tokens": 4000,
            "temperature": 0.1
        }
        
        return self._make_openai_request(openai_endpoint, headers, payload)
    
    def _make_openai_request(self, openai_endpoint, headers, payload):
        """
        Make the actual request to OpenAI API and handle the response
        
        Args:
            openai_endpoint: OpenAI API endpoint URL
            headers: Request headers including authorization
            payload: JSON payload for the API request
            
        Returns:
            dict: A structured dictionary containing:
                - extracted_text: The converted text content or empty string on failure
                - description: Additional context or document summary if available
                - __comment: Processing information or error message if conversion failed
        """
        logger = logging.getLogger(__name__)
        
        try:
            endpoint_url = f"{openai_endpoint}/v1/chat/completions"
            response = requests.post(endpoint_url, headers=headers, json=payload)
            
            if response.status_code == 200:
                result = response.json()
                content = result['choices'][0]['message']['content']
                
                # Try to parse as JSON first
                try:
                    import json
                    structured_result = json.loads(content)
                    logger.debug("Successfully parsed structured JSON response")
                    structured_result['__comment'] = "Converted using OpenAI."
                    return structured_result
                except json.JSONDecodeError:
                    logger.warning("Response was not valid JSON, wrapping in structure")
                    return {
                        "extracted_text": "",
                        "description": "",
                        "__comment": "Converted using OpenAI. Response was not in expected JSON format; extracted_text is the raw return value."
                    }
            else:
                logger.error(f"OpenAI API returned status {response.status_code}: {response.text}")
                return {
                    "extracted_text": "",
                    "description": "",
                    "__comment": f"OpenAI API returned status {response.status_code}: {response.text}"
                }
                
        except Exception as e:
            logger.error(f"Error making OpenAI API request: {e}")
            return {
                "extracted_text": "",
                "description": "",
                "__comment": f"Error processing attachment with OpenAI: {e}"
            }

    def convert_to_markdown(self, file_path, file_name):
        """
        Convert a document to markdown, attempting to use OpenAI first if available, then Docling API
        
        Args:
            file_path: Path to the temporary file
            file_name: Original file name
            
        Returns:
            dict: A structured dictionary containing:
                - extracted_text: The converted markdown content
                - description: Additional description or context about the document
                - __comment: Information about which conversion method was used
        """
        logger = logging.getLogger(__name__)

        docling_address = os.getenv('DOCLING_ADDRESS')
        openai_endpoint = os.getenv('OPENAI_API_BASE')
        
        if openai_endpoint:
            logger.debug(f"OpenAI endpoint set to: {openai_endpoint}")
        if docling_address:
            logger.debug(f"Docling address set to: {docling_address}")
        else:
            logger.debug("No Docling address provided, using fallback method")
        
        # Use OpenAI endpoint if available
        if openai_endpoint:
            logger.debug(f"Using OpenAI endpoint: {openai_endpoint}")
            openai_result = self.convert_with_openai(file_path, file_name, openai_endpoint)
            if openai_result:
                return openai_result
            logger.warning("OpenAI conversion failed, falling back to other methods")
            
        # Try using Docling API next if available
        if docling_address:
            docling_result = self.convert_with_docling(file_path, file_name, docling_address)
            if docling_result:
                return docling_result
            logger.warning("Docling conversion failed, falling back to markitdown")
        
        # Fallback to markitdown with structured response
        try:
            logger.debug("Using MarkItDown as fallback conversion method")
            md = MarkItDown(enable_plugins=True)
            result = md.convert(file_path)
            markdown_content = result.text_content
            
            # Determine file extension for description
            _, extension = os.path.splitext(file_name)
            extension = extension.lower().lstrip('.')
            
            # Return in unified structured format
            return {
                "extracted_text": markdown_content,
                "description": "",
                "__comment": f"Document converted from {extension.upper() if extension else 'unknown format'} using MarkItDown fallback",
            }
        except Exception as e:
            logger.error(f"Error converting to markdown with MarkItDown: {e}")
            # Return error in structured format
            return {
                "extracted_text": "",
                "description": "",
                "__comment": f"Error processing attachment with MarkItDown: {e}"
            }
