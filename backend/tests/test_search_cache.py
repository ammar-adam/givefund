"""Search cache tests."""

from search_cache import get_cached, set_cached


def test_search_cache_roundtrip():
    set_cached("cancer", {"query": "cancer", "campaigns": [], "total": 0})
    hit = get_cached("cancer")
    assert hit is not None
    assert hit["query"] == "cancer"


def test_search_cache_miss():
    assert get_cached("zzzznotcached999") is None
