"""Capture Algolia credentials from a live GoFundMe page and paginate discover results."""

import logging
import os
from typing import Any, Optional
from urllib.parse import parse_qs, quote, urlparse

import httpx
from playwright.async_api import Page, Request

logger = logging.getLogger(__name__)

ALGOLIA_HOST = "https://e7phe9bb38-dsn.algolia.net/1/indexes/*/queries"
INDEX_NAME = "prod_funds_feed_replica_1"

CATEGORY_ALGOLIA_IDS: dict[str, int] = {
    "medical": 13,
    "memorial": 1,
    "emergency": 11,
    "charity": 13,
    "education": 2,
    "animal": 4,
    "environment": 8,
    "business": 6,
    "community": 5,
    "competition": 3,
    "creative": 7,
    "event": 10,
    "faith": 12,
    "family": 9,
    "sports": 14,
    "travel": 16,
    "volunteer": 18,
    "wishes": 17,
}

ATTRIBUTES = (
    '["balance","bene_name","charity_name","country","currencycode",'
    '"funddescription","fundname","goal_progress","goalamount",'
    '"last_donation_at","locationtext","objectID","projecttype",'
    '"thumb_img_url","url","username"]'
)


class AlgoliaSession:
    """Holds search-only API key captured from the browser session."""

    def __init__(self) -> None:
        self.app_id: Optional[str] = os.getenv("GFM_ALGOLIA_APP_ID")
        self.api_key: Optional[str] = os.getenv("GFM_ALGOLIA_API_KEY")
        self._captured = bool(self.app_id and self.api_key)

    def attach(self, page: Page) -> None:
        """Listen for Algolia POST requests and store credentials."""

        def on_request(request: Request) -> None:
            if self._captured or request.method != "POST":
                return
            if "algolia.net" not in request.url and "algolianet.com" not in request.url:
                return
            query = parse_qs(urlparse(request.url).query)
            app_id = (query.get("x-algolia-application-id") or [None])[0]
            api_key = (query.get("x-algolia-api-key") or [None])[0]
            if not app_id or not api_key:
                headers = {k.lower(): v for k, v in request.headers.items()}
                app_id = app_id or headers.get("x-algolia-application-id")
                api_key = api_key or headers.get("x-algolia-api-key")
            if app_id and api_key:
                self.app_id = app_id
                self.api_key = api_key
                self._captured = True
                logger.info("[algolia] captured credentials for app %s", self.app_id)

        page.on("request", on_request)

    @staticmethod
    def _app_from_url(url: str) -> Optional[str]:
        host = urlparse(url).hostname or ""
        return host.split(".")[0] if host and "." in host else None

    def ready(self) -> bool:
        return bool(self.app_id and self.api_key)

    def _base_params(self, page: int, hits_per_page: int, query: str = "") -> str:
        return (
            'analyticsTags=["page:discover"]'
            f"&attributesToRetrieve={ATTRIBUTES}"
            "&clickAnalytics=true"
            "&exactOnSingleWordQuery=word"
            "&highlightPostTag=__/ais-highlight__"
            "&highlightPreTag=__ais-highlight__"
            f"&hitsPerPage={hits_per_page}"
            f"&page={page}"
            f"&query={quote(query)}"
        )

    def build_params(self, category_id: int, page: int, hits_per_page: int) -> str:
        """Build Algolia query params matching GoFundMe discover format."""
        filters = (
            f"((category_id={category_id})) AND turn_off_donations=0 "
            "AND NOT campaign_tags:greylisted"
        )
        return (
            self._base_params(page, hits_per_page)
            + f"&filters={quote(filters)}"
            + "&optionalFacetFilters=(country:US<score=3>, user_language_locale:en_US<score=2>)"
        )

    def build_text_search_params(self, query: str, page: int, hits_per_page: int) -> str:
        """Full-text search across all active GoFundMe campaigns."""
        filters = "turn_off_donations=0 AND NOT campaign_tags:greylisted"
        return self._base_params(page, hits_per_page, query) + f"&filters={quote(filters)}"

    async def fetch_category_page(
        self,
        category_id: int,
        page: int,
        hits_per_page: int = 50,
    ) -> list[dict[str, Any]]:
        """Fetch one Algolia results page."""
        if not self.ready():
            return []

        body = {
            "requests": [
                {
                    "indexName": INDEX_NAME,
                    "params": self.build_params(category_id, page, hits_per_page),
                }
            ]
        }
        headers = {
            "X-Algolia-Application-Id": self.app_id,
            "X-Algolia-API-Key": self.api_key,
            "Content-Type": "application/json",
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(ALGOLIA_HOST, headers=headers, json=body)
            response.raise_for_status()
            data = response.json()

        hits: list[dict[str, Any]] = []
        for result in data.get("results", []):
            hits.extend(result.get("hits", []))
        return hits

    async def search_text(
        self,
        query: str,
        *,
        max_pages: int = 8,
        hits_per_page: int = 50,
    ) -> list[dict[str, Any]]:
        """Paginate Algolia for a free-text query (e.g. palestine, cancer)."""
        if not self.ready() or not query.strip():
            return []

        all_hits: list[dict[str, Any]] = []
        for page_num in range(max_pages):
            body = {
                "requests": [
                    {
                        "indexName": INDEX_NAME,
                        "params": self.build_text_search_params(
                            query.strip(), page_num, hits_per_page
                        ),
                    }
                ]
            }
            headers = {
                "X-Algolia-Application-Id": self.app_id,
                "X-Algolia-API-Key": self.api_key,
                "Content-Type": "application/json",
            }
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(ALGOLIA_HOST, headers=headers, json=body)
                response.raise_for_status()
                data = response.json()

            page_hits: list[dict[str, Any]] = []
            for result in data.get("results", []):
                page_hits.extend(result.get("hits", []))
            if not page_hits:
                break
            all_hits.extend(page_hits)
            if len(page_hits) < hits_per_page:
                break
        logger.info("[algolia] search %r -> %d hits", query, len(all_hits))
        return all_hits
