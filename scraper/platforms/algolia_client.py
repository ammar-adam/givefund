"""Capture Algolia credentials from a live GoFundMe page and paginate discover results."""

import logging
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
        self.app_id: Optional[str] = None
        self.api_key: Optional[str] = None
        self._captured = False

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

    def build_params(self, category_id: int, page: int, hits_per_page: int) -> str:
        """Build Algolia query params matching GoFundMe discover format."""
        filters = (
            f"((category_id={category_id})) AND turn_off_donations=0 "
            "AND NOT campaign_tags:greylisted"
        )
        return (
            'analyticsTags=["page:discover"]'
            f"&attributesToRetrieve={ATTRIBUTES}"
            "&clickAnalytics=true"
            "&exactOnSingleWordQuery=word"
            f"&filters={quote(filters)}"
            "&highlightPostTag=__/ais-highlight__"
            "&highlightPreTag=__ais-highlight__"
            f"&hitsPerPage={hits_per_page}"
            "&optionalFacetFilters=(country:US<score=3>, user_language_locale:en_US<score=2>)"
            f"&page={page}"
            "&query="
        )

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
