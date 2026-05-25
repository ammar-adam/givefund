"""Platform scraper registry."""

from platforms.gofundme import scrape_gofundme
from platforms.launchgood import scrape_launchgood
from platforms.fundly import scrape_fundly

PLATFORM_SCRAPERS = {
    "gofundme": scrape_gofundme,
    "launchgood": scrape_launchgood,
    "fundly": scrape_fundly,
}

ALL_PLATFORMS = list(PLATFORM_SCRAPERS.keys())
