"""Discover configs for platforms beyond GoFundMe / LaunchGood / Fundly."""

from platforms.discover import DiscoverConfig, make_scraper

EXTRA_CONFIGS: list[DiscoverConfig] = [
    DiscoverConfig(
        platform="justgiving",
        base_url="https://www.justgiving.com",
        start_urls=("https://www.justgiving.com/crowdfunding",),
        link_markers=("/fundraising/", "/crowdfunding/"),
        card_selectors=("a[href*='/fundraising/']", "article"),
    ),
    DiscoverConfig(
        platform="gogetfunding",
        base_url="https://gogetfunding.com",
        start_urls=("https://gogetfunding.com/", "https://gogetfunding.com/browse/"),
        link_markers=("/fundraiser/", "/project/"),
    ),
    DiscoverConfig(
        platform="givebutter",
        base_url="https://givebutter.com",
        start_urls=("https://givebutter.com/explore",),
        link_markers=("/campaign/", "/f/"),
    ),
    DiscoverConfig(
        platform="mightycause",
        base_url="https://www.mightycause.com",
        start_urls=("https://www.mightycause.com/discover",),
        link_markers=("/story/", "/fundraiser/"),
    ),
    DiscoverConfig(
        platform="chuffed",
        base_url="https://chuffed.org",
        start_urls=("https://chuffed.org/explore",),
        link_markers=("/project/",),
    ),
    DiscoverConfig(
        platform="fundrazr",
        base_url="https://fundrazr.com",
        start_urls=("https://fundrazr.com/crowdfunding/projects",),
        link_markers=("/campaigns/", "/project/"),
    ),
    DiscoverConfig(
        platform="ketto",
        base_url="https://www.ketto.org",
        start_urls=(
            "https://www.ketto.org/crowdfunding/fundraisers",
            "https://www.ketto.org/medical-fundraising",
        ),
        link_markers=("/fundraiser/", "/crowdfunding/"),
        max_campaigns=40,
    ),
    DiscoverConfig(
        platform="mchanga",
        base_url="https://www.mchanga.africa",
        start_urls=("https://www.mchanga.africa/", "https://www.mchanga.africa/explore"),
        link_markers=("/fundraiser/", "/campaign/", "/f/"),
        max_campaigns=35,
    ),
    DiscoverConfig(
        platform="backabuddy",
        base_url="https://www.backabuddy.co.za",
        start_urls=("https://www.backabuddy.co.za/", "https://www.backabuddy.co.za/campaigns"),
        link_markers=("/campaign/", "/buddy/", "/project/"),
        max_campaigns=40,
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
]

EXTRA_SCRAPERS = {cfg.platform: make_scraper(cfg) for cfg in EXTRA_CONFIGS}
