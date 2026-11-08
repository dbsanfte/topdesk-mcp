import json
import pytest
from unittest.mock import Mock, patch
from urllib.parse import urlparse, parse_qs
from topdesk_mcp import _knowledge


def make_response(status_code, body=None):
    response = Mock()
    response.status_code = status_code
    response.headers = {'Content-Type': 'application/json'}
    response.text = json.dumps(body) if body is not None else ''
    response.json.return_value = body
    return response


def make_item(number, title, keywords=""):
    return {"id": number, "number": number,
            "translation": {"content": {"title": title, "description": "", "keywords": keywords}}}


def requested_params(url):
    return parse_qs(urlparse(url).query)


class TestKnowledgeItemGetPage:
    @pytest.fixture
    def knowledge_item(self):
        return _knowledge.knowledge_item("https://test.topdesk.net", "dGVzdDp0ZXN0")

    def test_requests_one_compact_page(self, knowledge_item):
        response = make_response(200, {"item": [make_item("KI 0001", "VPN")], "next": "more"})
        with patch('topdesk_mcp._utils.requests.get', return_value=response) as mock_get:
            result = knowledge_item.get_page(page_size=1, start=4)
        params = requested_params(mock_get.call_args[0][0])
        assert urlparse(mock_get.call_args[0][0]).path == _knowledge.knowledge_item.BASE_URI
        assert params['fields'] == [_knowledge.knowledge_item.PAGE_DEFAULT_FIELDS]
        assert params['query'] == ["archived==false"]
        assert params['page_size'] == ["1"]
        assert result['count'] == 1
        assert result['more_available'] is True
        assert result['next_start'] == 5

    def test_default_fields_exclude_fields_the_api_rejects(self):
        for fields in (_knowledge.knowledge_item.PAGE_DEFAULT_FIELDS, _knowledge.knowledge_item.ITEM_FIELDS):
            assert not {"id", "number", "archived"} & set(fields.split(","))

    def test_no_content_is_an_empty_last_page(self, knowledge_item):
        with patch('topdesk_mcp._utils.requests.get', return_value=make_response(204)):
            result = knowledge_item.get_page(archived=None)
        assert result['knowledge_items'] == []
        assert result['more_available'] is False
        assert result['next_start'] is None

    def test_text_search_scans_all_pages_and_filters_locally(self, knowledge_item):
        pages = [
            make_response(200, {"item": [make_item("KI 1", "VPN einrichten"), make_item("KI 2", "Drucker")], "next": "more"}),
            make_response(200, {"item": [make_item("KI 3", "Outlook", keywords="vpn,mac")]}),
        ]
        with patch('topdesk_mcp._utils.requests.get', side_effect=pages) as mock_get:
            result = knowledge_item.get_page(search_text="vpn", page_size=1)
            second = knowledge_item.get_page(search_text="vpn", page_size=1, start=1)
        assert mock_get.call_count == 2  # the second call is served from the cache
        params = requested_params(mock_get.call_args_list[0][0][0])
        assert params['fields'] == ["title,description,status,modificationDate,keywords"]
        assert params['page_size'] == [str(_knowledge.knowledge_item.SCAN_PAGE_SIZE)]
        assert [i['number'] for i in result['knowledge_items']] == ["KI 1"]
        assert result['total_matches'] == 2
        assert result['next_start'] == 1
        assert [i['number'] for i in second['knowledge_items']] == ["KI 3"]
        assert second['more_available'] is False

    def test_text_search_requires_all_words(self, knowledge_item):
        response = make_response(200, {"item": [make_item("KI 1", "VPN Mac"), make_item("KI 2", "VPN Windows")]})
        with patch('topdesk_mcp._utils.requests.get', return_value=response):
            result = knowledge_item.get_page(search_text="mac VPN")
        assert [i['number'] for i in result['knowledge_items']] == ["KI 1"]

    def test_error_keeps_topdesk_details(self, knowledge_item):
        body = {"errors": [{"errorCode": "field_invalid"}]}
        with patch('topdesk_mcp._utils.requests.get', return_value=make_response(400, body)):
            result = knowledge_item.get_page()
        assert result['status_code'] == 400
        assert "field_invalid" in result['details']


class TestKnowledgeItemGet:
    @pytest.fixture
    def knowledge_item(self):
        return _knowledge.knowledge_item("https://test.topdesk.net", "dGVzdDp0ZXN0")

    def test_get_by_number_quotes_the_path(self, knowledge_item):
        item = make_item("KI 0908", "Outlook")
        with patch('topdesk_mcp._utils.requests.get', return_value=make_response(200, item)) as mock_get:
            result = knowledge_item.get(" KI 0908 ", language="en")
        url = mock_get.call_args[0][0]
        assert urlparse(url).path == _knowledge.knowledge_item.BASE_URI + "/KI%200908"
        assert requested_params(url)['language'] == ["en"]
        assert result == item

    def test_get_error_is_a_dict(self, knowledge_item):
        with patch('topdesk_mcp._utils.requests.get', return_value=make_response(404, {"errors": []})):
            result = knowledge_item.get("KI 9999")
        assert result['status_code'] == 404
