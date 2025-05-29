import pytest
import requests
import json
import re
import os
import logging
from unittest.mock import Mock, patch, MagicMock, mock_open
from topdesk_mcp._utils import utils
from urllib.parse import parse_qs
from markitdown import MarkItDown

class TestUtils:
    
    @pytest.fixture
    def utils_instance(self):
        """Create a utils instance for testing."""
        return utils("https://test.topdesk.net", "dGVzdDp0ZXN0")
    
    @pytest.fixture
    def mock_response(self):
        """Create a mock response object."""
        response = Mock()
        response.status_code = 200
        response.json.return_value = {"test": "data"}
        response.text = '{"test": "data"}'
        response.url = "https://test.topdesk.net/tas/api/test"
        response.headers = {}
        return response

    def test_init_with_ssl_verify_true(self):
        """Test initialization with SSL verification enabled."""
        with patch.dict(os.environ, {'SSL_VERIFY': 'true'}):
            util = utils("https://test.topdesk.net", "credentials")
            assert util._ssl_verify is True

    def test_init_with_ssl_verify_false(self):
        """Test initialization with SSL verification disabled."""
        with patch.dict(os.environ, {'SSL_VERIFY': 'false'}):
            util = utils("https://test.topdesk.net", "credentials")
            assert util._ssl_verify is False

    def test_init_with_ssl_verify_default(self):
        """Test initialization with default SSL verification."""
        with patch.dict(os.environ, {}, clear=True):
            util = utils("https://test.topdesk.net", "credentials")
            assert util._ssl_verify is True

    def test_is_valid_uuid_valid(self, utils_instance):
        """Test valid UUID validation."""
        valid_uuid = "12345678-1234-1234-1234-123456789abc"
        result = utils_instance.is_valid_uuid(valid_uuid)
        assert result is not None

    def test_is_valid_uuid_invalid(self, utils_instance):
        """Test invalid UUID validation."""
        invalid_uuids = [
            "invalid-uuid",
            "12345678-1234-1234-1234",
            "12345678-1234-1234-1234-123456789abcg",  # contains 'g'
            "",
            "12345678-1234-1234-1234-123456789abcd"  # too long
        ]
        for invalid_uuid in invalid_uuids:
            result = utils_instance.is_valid_uuid(invalid_uuid)
            assert result is None

    def test_is_valid_email_addr_valid(self, utils_instance):
        """Test valid email address validation."""
        valid_emails = [
            "test@example.com",
            "user.name@domain.co.uk",
            "test123@test-domain.org"
        ]
        for email in valid_emails:
            result = utils_instance.is_valid_email_addr(email)
            assert result is not None

    def test_is_valid_email_addr_invalid(self, utils_instance):
        """Test invalid email address validation."""
        invalid_emails = [
            "invalid-email",
            "@domain.com",
            "test@",
            "test.domain.com",
            ""
        ]
        for email in invalid_emails:
            result = utils_instance.is_valid_email_addr(email)
            assert result is None

    @patch('topdesk_mcp._utils.requests.get')
    def test_request_topdesk_basic(self, mock_get, utils_instance, mock_response):
        """Test basic request_topdesk functionality."""
        mock_get.return_value = mock_response
        
        result = utils_instance.request_topdesk("/tas/api/test")
        
        mock_get.assert_called_once()
        args, kwargs = mock_get.call_args
        assert kwargs['headers']['Authorization'] == "Basic dGVzdDp0ZXN0"
        assert kwargs['verify'] == utils_instance._ssl_verify

    def test_handle_topdesk_response_success_200(self, utils_instance, mock_response):
        """Test handling successful 200 response."""
        mock_response.status_code = 200
        result = utils_instance.handle_topdesk_response(mock_response)
        assert result is not None

    def test_handle_topdesk_response_success_201(self, utils_instance, mock_response):
        """Test handling successful 201 response."""
        mock_response.status_code = 201
        result = utils_instance.handle_topdesk_response(mock_response)
        assert result is not None

    def test_handle_topdesk_response_no_content(self, utils_instance, mock_response):
        """Test handling 204 No Content response."""
        mock_response.status_code = 204
        result = utils_instance.handle_topdesk_response(mock_response)
        assert result is not None

    @patch.object(utils, '_handle_partial_content')
    def test_handle_topdesk_response_partial_content(self, mock_partial, utils_instance, mock_response):
        """Test handling 206 Partial Content response."""
        mock_response.status_code = 206
        mock_partial.return_value = {"test": "data"}
        
        result = utils_instance.handle_topdesk_response(mock_response)
        mock_partial.assert_called_once_with(mock_response)

    def test_handle_topdesk_response_client_errors(self, utils_instance, mock_response):
        """Test handling various client error responses."""
        error_codes = [400, 401, 403, 404, 409]
        for code in error_codes:
            mock_response.status_code = code
            result = utils_instance.handle_topdesk_response(mock_response)
            assert isinstance(result, str)  # Assuming errors return strings

    def test_handle_topdesk_response_server_errors(self, utils_instance, mock_response):
        """Test handling server error responses."""
        mock_response.status_code = 500
        result = utils_instance.handle_topdesk_response(mock_response)
        assert isinstance(result, str)

    def test_get_filename_from_headers_with_filename(self, utils_instance):
        """Test extracting filename from Content-Disposition header."""
        headers = {'Content-Disposition': 'attachment; filename="test.pdf"'}
        filename = utils_instance._get_filename_from_headers(headers)
        assert filename == "test.pdf"

    def test_get_filename_from_headers_without_filename(self, utils_instance):
        """Test default filename when Content-Disposition header is missing."""
        headers = {}
        filename = utils_instance._get_filename_from_headers(headers)
        assert filename == "downloaded_file"

    @patch.object(utils, 'request_topdesk')
    @patch.object(utils, 'handle_topdesk_response')
    def test_handle_partial_content(self, mock_handle, mock_request, utils_instance, mock_response):
        """Test handling partial content pagination."""
        mock_response.json.return_value = [{"id": 1}, {"id": 2}]
        mock_response.url = "https://test.topdesk.net/tas/api/test?page_size=10&start=0"
        
        mock_next_response = Mock()
        mock_request.return_value = mock_next_response
        mock_handle.return_value = {"final": "result"}
        
        utils_instance._partial_content_container = []
        result = utils_instance._handle_partial_content(mock_response)
        
        assert len(utils_instance._partial_content_container) == 2
        mock_request.assert_called_once()
        mock_handle.assert_called_once()

    @patch('topdesk_mcp._utils.requests.post')
    def test_post_to_topdesk(self, mock_post, utils_instance, mock_response):
        """Test POST request to TOPdesk."""
        mock_post.return_value = mock_response
        json_body = {"test": "data"}
        
        result = utils_instance.post_to_topdesk("/tas/api/test", json_body)
        
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        assert kwargs['json'] == json_body
        assert kwargs['headers']['Authorization'] == "Basic dGVzdDp0ZXN0"

    @patch('topdesk_mcp._utils.requests.put')
    def test_put_to_topdesk(self, mock_put, utils_instance, mock_response):
        """Test PUT request to TOPdesk."""
        mock_put.return_value = mock_response
        json_body = {"test": "data"}
        
        result = utils_instance.put_to_topdesk("/tas/api/test", json_body)
        
        mock_put.assert_called_once()
        args, kwargs = mock_put.call_args
        assert kwargs['json'] == json_body

    def test_client_error_messages(self, utils_instance, mock_response):
        """Test specific client error message handling."""
        test_cases = [
            (400, "Bad Request"),
            (401, "Unauthorized"),
            (403, "Forbidden"),
            (404, "Not Found"),
            (409, "Conflict")
        ]
        
        for status_code, expected_text in test_cases:
            mock_response.status_code = status_code
            mock_response.text = expected_text
            result = utils_instance._handle_client_error(mock_response)
            assert expected_text in result or str(status_code) in result

    def test_server_error_handling(self, utils_instance, mock_response):
        """Test server error handling."""
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        
        result = utils_instance._handle_server_error(mock_response)
        assert "Server Error 500" in result

    def test_resolve_lookup_candidates_single(self, utils_instance):
        """Test resolve_lookup_candidates with single candidate."""
        candidates = [{"id": "123", "name": "test"}]
        result = utils_instance.resolve_lookup_candidates(candidates)
        assert result is not None

    def test_resolve_lookup_candidates_multiple(self, utils_instance):
        """Test resolve_lookup_candidates with multiple candidates."""
        candidates = [
            {"id": "123", "name": "test1"},
            {"id": "456", "name": "test2"}
        ]
        result = utils_instance.resolve_lookup_candidates(candidates)
        assert result is not None

    def test_resolve_lookup_candidates_empty(self, utils_instance):
        """Test resolve_lookup_candidates with empty list."""
        candidates = []
        result = utils_instance.resolve_lookup_candidates(candidates)
        assert result is not None

    @patch('topdesk_mcp._utils.requests.get')
    def test_request_topdesk_with_all_params(self, mock_get, utils_instance, mock_response):
        """Test request_topdesk with all parameters."""
        mock_get.return_value = mock_response
        
        result = utils_instance.request_topdesk(
            "/tas/api/test",
            archived=True,
            page_size=50,
            query="test query",
            custom_uri={"param1": "value1", "param2": "value2"},
            extended_uri={"extended": "value"}
        )
        
        mock_get.assert_called_once()

    @patch('topdesk_mcp._utils.requests.patch')
    def test_patch_to_topdesk(self, mock_patch, utils_instance, mock_response):
        """Test PATCH request to TOPdesk."""
        mock_patch.return_value = mock_response
        json_body = {"test": "data"}
        
        result = utils_instance.patch_to_topdesk("/tas/api/test", json_body)
        
        mock_patch.assert_called_once()
        args, kwargs = mock_patch.call_args
        assert kwargs['json'] == json_body
        assert kwargs['headers']['Authorization'] == "Basic dGVzdDp0ZXN0"

    @patch('topdesk_mcp._utils.requests.delete')
    def test_delete_from_topdesk(self, mock_delete, utils_instance, mock_response):
        """Test DELETE request to TOPdesk."""
        mock_delete.return_value = mock_response
        json_body = {"test": "data"}
        
        result = utils_instance.delete_from_topdesk("/tas/api/test", json_body)
        
        mock_delete.assert_called_once()

    def test_other_error_handling_fallback(self, utils_instance, mock_response):
        """Test handling other errors fallback case."""
        mock_response.status_code = 422
        mock_response.json.return_value = {"unexpected": "format"}
        
        result = utils_instance._handle_other_error(mock_response)
        assert result is not None

    def test_handle_partial_content_no_page_size(self, utils_instance, mock_response):
        """Test handling partial content without page_size in URL."""
        with patch.object(utils_instance, 'request_topdesk') as mock_request, \
             patch.object(utils_instance, 'handle_topdesk_response') as mock_handle:
            
            mock_response.json.return_value = [{"id": 1}]
            mock_response.url = "https://test.topdesk.net/tas/api/test"
            
            mock_next_response = Mock()
            mock_request.return_value = mock_next_response
            mock_handle.return_value = {"final": "result"}
            
            utils_instance._partial_content_container = []
            result = utils_instance._handle_partial_content(mock_response)
            
            assert len(utils_instance._partial_content_container) == 1

    def test_handle_partial_content_existing_start_param(self, utils_instance, mock_response):
        """Test handling partial content with existing start parameter."""
        with patch.object(utils_instance, 'request_topdesk') as mock_request, \
             patch.object(utils_instance, 'handle_topdesk_response') as mock_handle:
            
            mock_response.json.return_value = [{"id": 1}]
            mock_response.url = "https://test.topdesk.net/tas/api/test?start=0&page_size=10"
            
            mock_next_response = Mock()
            mock_request.return_value = mock_next_response
            mock_handle.return_value = {"final": "result"}
            
            utils_instance._partial_content_container = []
            result = utils_instance._handle_partial_content(mock_response)
            
            mock_request.assert_called_once()

    def test_get_filename_from_headers_with_quotes(self, utils_instance):
        """Test extracting filename with quotes from header."""
        headers = {'Content-Disposition': 'attachment; filename=test.pdf'}
        filename = utils_instance._get_filename_from_headers(headers)
        assert filename == "test.pdf"

    def test_client_error_generic(self, utils_instance, mock_response):
        """Test generic client error handling."""
        mock_response.status_code = 418  # I'm a teapot
        mock_response.text = "Teapot Error"
        
        result = utils_instance._handle_client_error(mock_response)
        assert "418" in result

    @patch('topdesk_mcp._utils.os.getenv')
    @patch.object(utils, '_convert_image_with_openai')
    def test_convert_with_openai_image(self, mock_convert_image, mock_getenv, utils_instance):
        """Test convert_with_openai for image files."""
        mock_getenv.return_value = "test-api-key"
        mock_convert_image.return_value = "converted image content"
        
        result = utils_instance.convert_with_openai("/path/to/image.jpg", "image.jpg", "http://openai:8080")
        
        mock_convert_image.assert_called_once()

    @patch('topdesk_mcp._utils.os.getenv')
    @patch.object(utils, '_convert_document_with_openai')
    def test_convert_with_openai_document(self, mock_convert_doc, mock_getenv, utils_instance):
        """Test convert_with_openai for document files."""
        mock_getenv.return_value = "test-api-key"
        mock_convert_doc.return_value = "converted document content"
        
        result = utils_instance.convert_with_openai("/path/to/doc.pdf", "doc.pdf", "http://openai:8080")
        
        mock_convert_doc.assert_called_once()

    def test_handle_topdesk_response_other_status(self, utils_instance, mock_response):
        """Test handling response with other status codes."""
        mock_response.status_code = 300  # Redirection
        result = utils_instance.handle_topdesk_response(mock_response)
        assert result is not None

    @patch('urllib3.disable_warnings')
    def test_ssl_verify_warning_suppression(self, mock_disable_warnings):
        """Test SSL warning suppression when SSL verification is disabled."""
        with patch.dict(os.environ, {'SSL_VERIFY': 'false'}):
            util = utils("https://test.topdesk.net", "credentials")
            mock_disable_warnings.assert_called_once()

    @patch('topdesk_mcp._utils.requests.post')
    def test_make_openai_request(self, mock_post, utils_instance):
        """Test _make_openai_request method."""
        mock_response = Mock()
        mock_response.json.return_value = {"choices": [{"message": {"content": "response"}}]}
        mock_post.return_value = mock_response
        
        headers = {"Authorization": "Bearer test-key"}
        payload = {"test": "data"}
        
        result = utils_instance._make_openai_request("http://openai:8080", headers, payload)
        
        mock_post.assert_called_once()

    @patch('topdesk_mcp._utils.os.getenv')
    def test_convert_with_openai_unsupported_filetype(self, mock_getenv, utils_instance):
        """Test convert_with_openai with unsupported file type."""
        mock_getenv.return_value = "test-api-key"
        
        result = utils_instance.convert_with_openai("/path/to/file.xyz", "file.xyz", "http://openai:8080")
        
        assert "__comment" in result
        assert "Unsupported file extension" in result["__comment"]
        assert result["extracted_text"] == ""
        
    @patch('topdesk_mcp._utils.os.getenv')
    def test_convert_with_openai_missing_api_key(self, mock_getenv, utils_instance):
        """Test convert_with_openai with missing API key."""
        mock_getenv.return_value = None
        
        result = utils_instance.convert_with_openai("/path/to/doc.pdf", "doc.pdf", "http://openai:8080")
        
        assert "__comment" in result
        assert "OPENAI_API_KEY not found" in result["__comment"]
        assert result["extracted_text"] == ""
        
    @patch('topdesk_mcp._utils.os.getenv')
    @patch('topdesk_mcp._utils.requests.post')
    def test_make_openai_request_success(self, mock_post, mock_getenv, utils_instance):
        """Test _make_openai_request with successful response."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": '{"extracted_text": "Test content", "description": "Test description"}'}}]
        }
        mock_post.return_value = mock_response
        
        headers = {"Authorization": "Bearer test-key"}
        payload = {"test": "data"}
        
        result = utils_instance._make_openai_request("http://openai:8080", headers, payload)
        
        assert result["extracted_text"] == "Test content"
        assert result["description"] == "Test description"
        assert "__comment" in result
        mock_post.assert_called_once()
        
    @patch('topdesk_mcp._utils.os.getenv')
    @patch('topdesk_mcp._utils.requests.post')
    def test_make_openai_request_error(self, mock_post, mock_getenv, utils_instance):
        """Test _make_openai_request with error response."""
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.text = "Bad Request"
        mock_post.return_value = mock_response
        
        headers = {"Authorization": "Bearer test-key"}
        payload = {"test": "data"}
        
        result = utils_instance._make_openai_request("http://openai:8080", headers, payload)
        
        assert result["extracted_text"] == ""
        assert "__comment" in result
        assert "400" in result["__comment"]
        mock_post.assert_called_once()
        
    @patch('topdesk_mcp._utils.os.getenv')
    @patch('topdesk_mcp._utils.requests.post')
    def test_make_openai_request_invalid_json(self, mock_post, mock_getenv, utils_instance):
        """Test _make_openai_request with non-JSON response."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Not a JSON string"}}]
        }
        mock_post.return_value = mock_response
        
        headers = {"Authorization": "Bearer test-key"}
        payload = {"test": "data"}
        
        result = utils_instance._make_openai_request("http://openai:8080", headers, payload)
        
        assert "__comment" in result
        assert "not in expected JSON format" in result["__comment"]
        mock_post.assert_called_once()
        
    @patch('topdesk_mcp._utils.os')
    @patch('topdesk_mcp._utils.requests.post')
    def test_convert_document_with_openai_pdf(self, mock_post, mock_os, utils_instance):
        """Test _convert_document_with_openai with PDF file."""
        # Setup mocks
        mock_os.path.splitext.return_value = ("path", ".pdf")
        mock_os.getenv.return_value = "test-api-key"
        
        mock_file = mock_open(read_data=b'test file content')
        with patch('builtins.open', mock_file):
            with patch.object(utils_instance, '_make_openai_request') as mock_make_request:
                mock_make_request.return_value = {
                    "extracted_text": "PDF content",
                    "description": "PDF description"
                }
                
                result = utils_instance._convert_document_with_openai(
                    "/path/to/doc.pdf", "doc.pdf", "pdf", "http://openai:8080", "test-api-key"
                )
                
                assert result["extracted_text"] == "PDF content"
                assert result["description"] == "PDF description"
                
                # Verify proper payload was constructed
                args = mock_make_request.call_args
                payload = args[0][2]
                assert "model" in payload
                assert "messages" in payload
                assert any("PDF" in msg.get("content", "") for msg in payload["messages"] if msg["role"] == "system")
                
    @patch('topdesk_mcp._utils.os')
    @patch('topdesk_mcp._utils.requests.post')
    def test_convert_document_with_openai_csv(self, mock_post, mock_os, utils_instance):
        """Test _convert_document_with_openai with CSV file."""
        # Setup mocks
        mock_os.path.splitext.return_value = ("path", ".csv")
        mock_os.getenv.return_value = "test-api-key"
        
        csv_content = b'header1,header2\nvalue1,value2'
        mock_file = mock_open(read_data=csv_content)
        with patch('builtins.open', mock_file):
            with patch.object(utils_instance, '_make_openai_request') as mock_make_request:
                mock_make_request.return_value = {
                    "extracted_text": "CSV content in markdown",
                    "description": "CSV description"
                }
                
                result = utils_instance._convert_document_with_openai(
                    "/path/to/file.csv", "file.csv", "csv", "http://openai:8080", "test-api-key"
                )
                
                assert result["extracted_text"] == "CSV content in markdown"
                assert result["description"] == "CSV description"
                
                # Verify CSV-specific logic was used
                args = mock_make_request.call_args
                payload = args[0][2]
                assert any("CSV" in msg.get("content", "") for msg in payload["messages"] if msg["role"] == "system")
                
    @patch('topdesk_mcp._utils.os')
    @patch('topdesk_mcp._utils.requests.post')
    def test_convert_image_with_openai(self, mock_post, mock_os, utils_instance):
        """Test _convert_image_with_openai directly."""
        # Setup mocks
        mock_os.path.splitext.return_value = ("path", ".jpg")
        mock_os.getenv.return_value = "test-api-key"
        
        image_content = b'fake image data'
        mock_file = mock_open(read_data=image_content)
        with patch('builtins.open', mock_file):
            with patch.object(utils_instance, '_make_openai_request') as mock_make_request:
                mock_make_request.return_value = {
                    "extracted_text": "Text from image",
                    "description": "Description of image"
                }
                
                result = utils_instance._convert_image_with_openai(
                    "/path/to/image.jpg", "image.jpg", "jpg", "http://openai:8080", "test-api-key"
                )
                
                assert result["extracted_text"] == "Text from image"
                assert result["description"] == "Description of image"
                
                # Verify image-specific logic was used
                args = mock_make_request.call_args
                payload = args[0][2]
                assert any("image" in str(msg.get("content", "")).lower() 
                          for msg in payload["messages"] if msg["role"] == "user")
                          
    @patch('topdesk_mcp._utils.os.getenv')
    @patch('topdesk_mcp._utils.requests.post')
    def test_convert_with_docling(self, mock_post, mock_getenv, utils_instance):
        """Test convert_with_docling method."""
        # Setup response mock
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "document": {
                "md_content": "# Converted markdown content"
            }
        }
        mock_post.return_value = mock_response
        
        # Mock environment variables
        mock_getenv.side_effect = lambda x: "test-key" if x == "DOCLING_API_KEY" else None
        
        # Mock file open
        mock_file = mock_open(read_data=b'test file content')
        with patch('builtins.open', mock_file):
            result = utils_instance.convert_with_docling(
                "/path/to/doc.pdf", "doc.pdf", "http://docling:8080"
            )
            
            assert "extracted_text" in result
            assert result["extracted_text"] == "# Converted markdown content"
            assert "__comment" in result
            assert "Document converted" in result["__comment"]
            
            # Verify API call was made correctly
            mock_post.assert_called_once()
            args, kwargs = mock_post.call_args
            assert kwargs['headers']['Authorization'].startswith('Bearer ')
            assert 'files' in kwargs
            assert kwargs['data']['from_formats'] == 'pdf'
            
    @patch('topdesk_mcp._utils.os.getenv')
    @patch('topdesk_mcp._utils.requests.post')
    def test_convert_with_docling_error(self, mock_post, mock_getenv, utils_instance):
        """Test convert_with_docling with error response."""
        # Setup response mock
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.text = "Bad Request"
        mock_post.return_value = mock_response
        
        # Mock environment variables
        mock_getenv.side_effect = lambda x: "test-key" if x == "DOCLING_API_KEY" else None
        
        # Mock file open
        mock_file = mock_open(read_data=b'test file content')
        with patch('builtins.open', mock_file):
            result = utils_instance.convert_with_docling(
                "/path/to/doc.pdf", "doc.pdf", "http://docling:8080"
            )
            
            assert result["extracted_text"] == ""
            assert "__comment" in result
            assert "400" in result["__comment"]
            
    def test_add_id_list(self, utils_instance):
        """Test add_id_list method."""
        id_list = ["123", "456", "789"]
        result = utils_instance.add_id_list(id_list)
        
        assert len(result) == 3
        assert all("id" in item for item in result)
        assert [item["id"] for item in result] == id_list
        
    def test_add_id_jsonbody_with_uuid(self, utils_instance):
        """Test add_id_jsonbody with UUID values."""
        with patch.object(utils_instance, 'is_valid_uuid', return_value=True):
            result = utils_instance.add_id_jsonbody(
                category="12345678-1234-1234-1234-123456789abc",
                status="87654321-4321-4321-4321-cba987654321"
            )
            
            assert "category" in result
            assert "status" in result
            assert "id" in result["category"]
            assert "id" in result["status"]
            assert result["category"]["id"] == "12345678-1234-1234-1234-123456789abc"
            
    @patch('topdesk_mcp._utils.os.getenv')
    @patch('topdesk_mcp._utils.utils.convert_with_openai')
    @patch('topdesk_mcp._utils.utils.convert_with_docling')
    @patch('topdesk_mcp._utils.MarkItDown')
    def test_convert_to_markdown_openai_path(self, mock_md, mock_docling, mock_openai, mock_getenv, utils_instance):
        """Test convert_to_markdown using OpenAI path."""
        # Setup mocks
        mock_getenv.side_effect = lambda x: "http://openai:8080" if x == "OPENAI_API_BASE" else None
        mock_openai.return_value = {
            "extracted_text": "Markdown from OpenAI",
            "description": "OpenAI description"
        }
        
        result = utils_instance.convert_to_markdown("/path/to/doc.pdf", "doc.pdf")
        
        assert result["extracted_text"] == "Markdown from OpenAI"
        assert result["description"] == "OpenAI description"
        mock_openai.assert_called_once()
        mock_docling.assert_not_called()
        mock_md.assert_not_called()
        
    @patch('topdesk_mcp._utils.MarkItDown')
    @patch('topdesk_mcp._utils.utils.convert_with_docling')
    @patch('topdesk_mcp._utils.utils.convert_with_openai')
    @patch('topdesk_mcp._utils.os.getenv')
    def test_convert_to_markdown_docling_fallback(self, mock_getenv, mock_openai, mock_docling, mock_md, utils_instance):
        """Test convert_to_markdown with OpenAI failing and Docling fallback."""
        # Setup mocks
        mock_getenv.side_effect = lambda x: {
            "OPENAI_API_BASE": "http://openai:8080",
            "DOCLING_ADDRESS": "http://docling:8080"
        }.get(x)
        
        # Make OpenAI fail
        mock_openai.return_value = None
        
        # Make Docling succeed
        mock_docling.return_value = {
            "extracted_text": "Markdown from Docling",
            "description": "Docling description"
        }
        
        result = utils_instance.convert_to_markdown("/path/to/doc.pdf", "doc.pdf")
        
        assert result["extracted_text"] == "Markdown from Docling"
        mock_openai.assert_called_once()
        mock_docling.assert_called_once()
        mock_md.assert_not_called()
        
    @patch('topdesk_mcp._utils.os.getenv')
    @patch('topdesk_mcp._utils.utils.convert_with_openai')
    @patch('topdesk_mcp._utils.utils.convert_with_docling')
    @patch('topdesk_mcp._utils.MarkItDown')
    def test_convert_to_markdown_markitdown_fallback(self, mock_md, mock_docling, mock_openai, mock_getenv, utils_instance):
        """Test convert_to_markdown with all conversions falling back to MarkItDown."""
        # Setup mocks
        mock_getenv.return_value = None  # No external services
        
        # Setup markitdown mock
        mock_md_instance = Mock()
        mock_md_instance.convert.return_value = Mock(text_content="Markdown from MarkItDown")
        mock_md.return_value = mock_md_instance
        
        result = utils_instance.convert_to_markdown("/path/to/doc.pdf", "doc.pdf")
        
        assert "extracted_text" in result
        assert result["extracted_text"] == "Markdown from MarkItDown"
        assert "__comment" in result
        assert "MarkItDown" in result["__comment"]
        mock_openai.assert_not_called()
        mock_docling.assert_not_called()
        mock_md.assert_called_once()
