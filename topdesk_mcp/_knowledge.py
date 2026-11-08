from topdesk_mcp import _utils
import logging
import time
import urllib.parse

class knowledge_item:
    # Read-only access to the TOPdesk Knowledge Base API (knowledge-base-v1).
    # The API always returns id and number; requesting them (or archived) as fields is a 400.

    BASE_URI = "/services/knowledge-base-v1/knowledgeItems"

    # Default fields for get_page: enough to pick a knowledge item from a result list.
    PAGE_DEFAULT_FIELDS = "title,description,status,modificationDate"

    # Fields for get: the complete knowledge item including its content.
    ITEM_FIELDS = ("parent,visibility,manager,status,standardSolution,externalLink,"
                   "news,title,description,content,commentsForOperators,keywords,"
                   "creator,modifier,creationDate,modificationDate,availableTranslations")

    # The API cannot filter on title or keywords, so a text search loads these fields
    # for all matching knowledge items and filters locally.
    SEARCH_FIELDS = ("title", "description", "keywords")
    SCAN_PAGE_SIZE = 1000
    SCAN_CACHE_SECONDS = 300

    def __init__(self, topdesk_url, credpair):
        self._topdesk_url = topdesk_url
        self._credpair = credpair
        self.utils = _utils.utils(self._topdesk_url, self._credpair)
        self._scan_cache = {}
        self._logger = logging.getLogger(__name__)
        self._logger.debug("TOPdesk API knowledge_item object initialised.")

    def _request_page(self, query, fields, page_size, start, language):
        """Returns (items, more_available) or an error dict."""
        params = {'start': start, 'fields': fields}
        if language:
            params['language'] = language
        response = self.utils.request_topdesk(self.BASE_URI, page_size=page_size, query=query, extended_uri=params)
        if response.status_code == 204:
            return [], False
        if response.status_code not in (200, 206):
            return self._error(response)
        body = response.json()
        # The API wraps the list as {"item": [...], "next": "<url of next page>"}.
        if isinstance(body, dict):
            return body.get('item', []), bool(body.get('next'))
        return body, response.status_code == 206

    def _scan(self, query, fields, language):
        """Loads all knowledge items matching the FIQL query, cached for a few minutes."""
        key = (query, fields, language)
        cached = self._scan_cache.get(key)
        if cached and time.monotonic() - cached[0] < self.SCAN_CACHE_SECONDS:
            return cached[1]
        items, start = [], 0
        while True:
            page = self._request_page(query, fields, self.SCAN_PAGE_SIZE, start, language)
            if isinstance(page, dict):
                return page
            batch, more = page
            items += batch
            start += len(batch)
            if not more or not batch:
                break
        self._scan_cache = {key: (time.monotonic(), items)}
        return items

    @classmethod
    def _matches(cls, item, words):
        content = (item.get('translation') or {}).get('content') or {}
        text = " ".join(str(content.get(f) or "") for f in cls.SEARCH_FIELDS).lower()
        return all(word in text for word in words)

    def get_page(self, search_text=None, query=None, fields=None, page_size=20, start=0, language=None, archived=False):
        """
        Retrieves a single page of knowledge items.

        Args:
            search_text: Optional words that must all appear in title, description or keywords
                (case-insensitive). The API cannot filter on these, so the search runs locally
                over all knowledge items matching the other filters.
            query: Optional FIQL query, combined with archived using AND
            fields: Comma-separated fields to return. Empty = PAGE_DEFAULT_FIELDS
            page_size: Knowledge items per page (1-100)
            start: Offset of the first knowledge item
            language: Optional language of the translation, e.g. "de" or "en"
            archived: Whether to search archived knowledge items. None = both

        Returns:
            A dictionary with 'knowledge_items', 'count', 'start', 'more_available'
            and 'next_start' (plus 'total_matches' for a text search), or with 'error'.
        """
        page_size = max(1, min(int(page_size), 100))
        start = max(0, int(start))
        fields = (fields or "").replace(" ", "") or self.PAGE_DEFAULT_FIELDS

        conditions = []
        if archived is not None:
            conditions.append("archived=={}".format(str(archived).lower()))
        if query:
            conditions.append("({})".format(query))
        fiql = ";".join(conditions) or None

        words = (search_text or "").lower().split()
        if not words:
            page = self._request_page(fiql, fields, page_size, start, language)
            if isinstance(page, dict):
                return page
            items, more = page
            return {
                'knowledge_items': items,
                'count': len(items),
                'start': start,
                'more_available': more,
                'next_start': start + len(items) if more else None,
            }

        requested = fields.split(",")
        scan_fields = ",".join(requested + [f for f in self.SEARCH_FIELDS if f not in requested])
        items = self._scan(fiql, scan_fields, language)
        if isinstance(items, dict):
            return items
        matches = [item for item in items if self._matches(item, words)]
        page = matches[start:start + page_size]
        more = start + len(page) < len(matches)
        return {
            'knowledge_items': page,
            'count': len(page),
            'start': start,
            'total_matches': len(matches),
            'more_available': more,
            'next_start': start + len(page) if more else None,
        }

    def get(self, knowledge_item, language=None):
        """
        Retrieves a single knowledge item by UUID or number (e.g. KI 0123), including its content.
        """
        params = {'fields': self.ITEM_FIELDS}
        if language:
            params['language'] = language
        response = self.utils.request_topdesk("{}/{}".format(self.BASE_URI, urllib.parse.quote(knowledge_item.strip(), safe="")), extended_uri=params)
        if response.status_code != 200:
            return self._error(response)
        return response.json()

    def _error(self, response):
        # Keep TOPdesk's own error text: the knowledge base API explains invalid parameters there.
        return {
            'error': self.utils.handle_topdesk_response(response),
            'status_code': response.status_code,
            'details': response.text[:2000],
        }
