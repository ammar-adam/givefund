"""HTTP link extraction tests."""

from platforms.discover import DiscoverConfig, extract_hrefs_from_html


def test_extract_hrefs_basic():
    cfg = DiscoverConfig(
        platform="test",
        base_url="https://example.com",
        start_urls=("https://example.com",),
        link_markers=("/fundraiser/",),
        search_url_template="https://example.com/search?q={query}",
    )
    html = '<a href="https://example.com/fundraiser/help-maria">Help</a>'
    hrefs = extract_hrefs_from_html(html, cfg)
    assert "https://example.com/fundraiser/help-maria" in hrefs


def test_extract_hrefs_next_data():
    cfg = DiscoverConfig(
        platform="test",
        base_url="https://example.com",
        start_urls=("https://example.com",),
        link_markers=("/project/",),
    )
    html = """
    <script id="__NEXT_DATA__" type="application/json">
    {"props":{"pageProps":{"items":[{"url":"/project/cancer-relief"}]}}}
    </script>
    """
    hrefs = extract_hrefs_from_html(html, cfg)
    assert any("/project/cancer-relief" in h for h in hrefs)
