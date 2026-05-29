"""Discover configs for platforms beyond GoFundMe / LaunchGood / Fundly."""

from platforms.discover import DiscoverConfig, make_scraper

EXTRA_CONFIGS: list[DiscoverConfig] = [
    DiscoverConfig(
        platform="justgiving",
        base_url="https://www.justgiving.com",
        start_urls=("https://www.justgiving.com/crowdfunding",),
        link_markers=("/fundraising/", "/crowdfunding/"),
        card_selectors=("a[href*='/fundraising/']", "article"),
        search_url_template="https://www.justgiving.com/search?q={query}",
    ),
    DiscoverConfig(
        platform="gogetfunding",
        base_url="https://gogetfunding.com",
        start_urls=("https://gogetfunding.com/", "https://gogetfunding.com/browse/"),
        link_markers=("/fundraiser/", "/project/"),
        search_url_template="https://gogetfunding.com/search/{query}",
    ),
    DiscoverConfig(
        platform="givebutter",
        base_url="https://givebutter.com",
        start_urls=("https://givebutter.com/explore",),
        link_markers=("/campaign/", "/f/"),
        search_url_template="https://givebutter.com/explore?search={query}",
    ),
    DiscoverConfig(
        platform="mightycause",
        base_url="https://www.mightycause.com",
        start_urls=("https://www.mightycause.com/discover",),
        link_markers=("/story/", "/fundraiser/"),
        search_url_template="https://www.mightycause.com/search?q={query}",
    ),
    DiscoverConfig(
        platform="chuffed",
        base_url="https://chuffed.org",
        start_urls=("https://chuffed.org/explore",),
        link_markers=("/project/",),
        search_url_template="https://chuffed.org/explore?search={query}",
    ),
    DiscoverConfig(
        platform="fundrazr",
        base_url="https://fundrazr.com",
        start_urls=("https://fundrazr.com/crowdfunding/projects",),
        link_markers=("/campaigns/", "/project/"),
        search_url_template="https://fundrazr.com/crowdfunding/projects?search={query}",
    ),
    DiscoverConfig(
        platform="milaap",
        base_url="https://milaap.org",
        start_urls=("https://milaap.org/fundraisers", "https://milaap.org/"),
        link_markers=("/fundraisers/", "/fundraiser/"),
        search_url_template="https://milaap.org/search?q={query}",
    ),
    DiscoverConfig(
        platform="mchanga",
        base_url="https://www.mchanga.africa",
        start_urls=("https://www.mchanga.africa/", "https://www.mchanga.africa/explore"),
        link_markers=("/fundraiser/", "/campaign/", "/f/"),
        max_campaigns=35,
    ),
    DiscoverConfig(
        platform="giveasia",
        base_url="https://give.asia",
        start_urls=("https://give.asia/explore", "https://give.asia/campaigns"),
        link_markers=("/campaign/", "/project/"),
        max_campaigns=30,
    ),
    DiscoverConfig(
        platform="thundafund",
        base_url="https://www.thundafund.com",
        start_urls=("https://www.thundafund.com/explore", "https://www.thundafund.com/"),
        link_markers=("/project/", "/campaign/"),
        max_campaigns=25,
    ),
    DiscoverConfig(
        platform="donorbox",
        base_url="https://donorbox.org",
        start_urls=("https://donorbox.org/",),
        link_markers=("/campaign/",),
    ),
    DiscoverConfig(
        platform="patreon",
        base_url="https://www.patreon.com",
        start_urls=("https://www.patreon.com/discover",),
        link_markers=("/c/", "/user/"),
        max_campaigns=20,
    ),
    DiscoverConfig(
        platform="impactguru",
        base_url="https://www.impactguru.com",
        start_urls=("https://www.impactguru.com/explore",),
        link_markers=("/fundraiser/", "/campaign/"),
        search_url_template="https://www.impactguru.com/search?search={query}",
    ),
    DiscoverConfig(
        platform="whydonate",
        base_url="https://whydonate.com",
        start_urls=("https://whydonate.com/en/campaigns",),
        link_markers=("/campaign/", "/fundraiser/"),
        search_url_template="https://whydonate.com/en/search/{query}",
    ),
    DiscoverConfig(
        platform="givesendgo",
        base_url="https://www.givesendgo.com",
        start_urls=("https://www.givesendgo.com/site/browse",),
        link_markers=("/G", "/f/"),
        search_url_template="https://www.givesendgo.com/site/search?search={query}",
    ),
    DiscoverConfig(
        platform="givengain",
        base_url="https://www.givengain.com",
        start_urls=("https://www.givengain.com/campaigns",),
        link_markers=("/project/", "/campaign/"),
        search_url_template="https://www.givengain.com/search?q={query}",
    ),
    DiscoverConfig(
        platform="leetchi",
        base_url="https://www.leetchi.com",
        start_urls=("https://www.leetchi.com/en/collection", "https://www.leetchi.com/en/collections"),
        link_markers=("/c/", "/pot/"),
        max_campaigns=30,
    ),
]

EXTRA_SCRAPERS = {cfg.platform: make_scraper(cfg) for cfg in EXTRA_CONFIGS}
