import json
import pytest
from unittest.mock import Mock, patch
from urllib.parse import urlparse, parse_qs
from topdesk_mcp import _incident


def make_response(status_code, incidents=None):
    response = Mock()
    response.status_code = status_code
    response.headers = {'Content-Type': 'application/json'}
    response.text = json.dumps(incidents) if incidents is not None else ''
    response.json.return_value = incidents
    response.url = "https://test.topdesk.net/tas/api/incidents/"
    return response


def requested_params(mock_get):
    return parse_qs(urlparse(mock_get.call_args[0][0]).query)


def result_bytes(result):
    return len(json.dumps(result, ensure_ascii=False).encode("utf-8"))


class TestIncidentGetPage:
    @pytest.fixture
    def incident(self):
        return _incident.incident("https://test.topdesk.net", "dGVzdDp0ZXN0")

    def get_page(self, incident, response, **kwargs):
        with patch('topdesk_mcp._utils.requests.get', return_value=response) as mock_get:
            result = incident.get_page(**kwargs)
        return result, mock_get

    def test_requests_one_compact_page(self, incident):
        result, mock_get = self.get_page(incident, make_response(200, [{"number": "I1"}]), query="status==secondLine")
        params = requested_params(mock_get)
        assert mock_get.call_count == 1
        assert params['query'] == ["status==secondLine"]
        assert params['page_size'] == ["50"]
        assert params['start'] == ["0"]
        assert params['fields'] == [_incident.incident.PAGE_DEFAULT_FIELDS]
        assert 'sort' not in params
        assert 'archived' not in mock_get.call_args[0][0]

    def test_partial_content_reports_next_page(self, incident):
        page = [{"number": "I1"}, {"number": "I2"}]
        result, _ = self.get_page(incident, make_response(206, page), query="status==secondLine", page_size=2, start=4)
        assert result['incidents'] == page
        assert result['count'] == 2
        assert result['start'] == 4
        assert result['more_available'] is True
        assert result['next_start'] == 6
        assert 'note' not in result

    def test_last_page_has_no_next_start(self, incident):
        result, _ = self.get_page(incident, make_response(200, [{"number": "I1"}]), query="number==I1")
        assert result['more_available'] is False
        assert result['next_start'] is None

    def test_no_content(self, incident):
        result, _ = self.get_page(incident, make_response(204), query="number==none")
        assert result['incidents'] == []
        assert result['count'] == 0
        assert result['more_available'] is False

    def test_all_fields_sends_no_fields_parameter(self, incident):
        _, mock_get = self.get_page(incident, make_response(200, []), query="status==secondLine", fields="all")
        assert 'fields' not in requested_params(mock_get)

    def test_custom_fields_and_sort(self, incident):
        _, mock_get = self.get_page(incident, make_response(200, []), query="status==secondLine",
                                    fields="number, briefDescription", sort="callDate:desc")
        params = requested_params(mock_get)
        assert params['fields'] == ["number,briefDescription"]
        assert params['sort'] == ["callDate:desc"]

    @pytest.mark.parametrize("page_size, start, expected_size, expected_start", [
        (0, -5, "1", "0"),
        (1000, 10, "500", "10"),
    ])
    def test_page_size_and_start_are_clamped(self, incident, page_size, start, expected_size, expected_start):
        _, mock_get = self.get_page(incident, make_response(200, []), page_size=page_size, start=start)
        params = requested_params(mock_get)
        assert params['page_size'] == [expected_size]
        assert params['start'] == [expected_start]

    def test_page_is_shortened_to_size_budget(self, incident):
        page = [{"number": "I%d" % i, "request": "x" * 100} for i in range(5)]
        max_bytes = 600
        result, _ = self.get_page(incident, make_response(200, page), query="status==secondLine",
                                  start=10, max_bytes=max_bytes)
        assert 1 <= result['count'] < 5
        assert result_bytes(result) <= max_bytes
        assert result['more_available'] is True
        assert result['next_start'] == 10 + result['count']
        assert 'note' in result

    def test_non_ascii_page_stays_within_byte_budget(self, incident):
        # Characters outside ASCII take several bytes in UTF-8: 9,000 CJK characters
        # are about 27 KB, so 50 of them would exceed the default budget of 500 KB.
        page = [{"number": "I%d" % i, "request": "汉" * 9000} for i in range(50)]
        result, _ = self.get_page(incident, make_response(206, page), query="status==secondLine")
        assert result_bytes(result) <= _incident.incident.PAGE_MAX_BYTES
        assert 1 <= result['count'] < 50
        assert result['more_available'] is True
        assert result['next_start'] == result['count']
        assert 'note' in result

    def test_full_page_within_budget_is_not_shortened(self, incident):
        page = [{"number": "I%d" % i, "request": "ä" * 1000} for i in range(50)]
        result, _ = self.get_page(incident, make_response(200, page), query="status==secondLine")
        assert result['count'] == 50
        assert result['more_available'] is False
        assert 'note' not in result

    def test_oversized_first_incident_is_still_returned(self, incident):
        page = [{"number": "I1", "request": "x" * 1000}, {"number": "I2"}]
        result, _ = self.get_page(incident, make_response(206, page), query="status==secondLine", max_bytes=10)
        assert [i['number'] for i in result['incidents']] == ["I1"]
        assert result['next_start'] == 1

    def test_api_error_is_returned(self, incident):
        response = make_response(400)
        response.text = '[{"message":"query contains unknown field"}]'
        result, _ = self.get_page(incident, response, query="unknown==1")
        assert result == {'error': "Bad Request: The request was invalid or cannot be served."}
