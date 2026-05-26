"""Platform scraper registry."""

from platforms.backabuddy import scrape_backabuddy
from platforms.extra import EXTRA_SCRAPERS
from platforms.fundly import scrape_fundly
from platforms.globalgiving import scrape_globalgiving
from platforms.gofundme import scrape_gofundme
from platforms.islamicrelief import scrape_islamicrelief_ca
from platforms.ketto import scrape_ketto
from platforms.launchgood import scrape_launchgood

PLATFORM_SCRAPERS = {
    "gofundme": scrape_gofundme,
    "launchgood": scrape_launchgood,
    "fundly": scrape_fundly,
    "globalgiving": scrape_globalgiving,
    "islamicrelief_ca": scrape_islamicrelief_ca,
    "ketto": scrape_ketto,
    "backabuddy": scrape_backabuddy,
    **EXTRA_SCRAPERS,
}

ALL_PLATFORMS = list(PLATFORM_SCRAPERS.keys())
