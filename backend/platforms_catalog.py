"""Supported crowdfunding platforms (scraper + discovery UI)."""

PLATFORM_CATALOG: list[dict[str, str]] = [
    {"id": "gofundme", "label": "GoFundMe"},
    {"id": "launchgood", "label": "LaunchGood"},
    {"id": "fundly", "label": "Fundly"},
    {"id": "islamicrelief_ca", "label": "Islamic Relief (Canada)"},
    {"id": "ketto", "label": "Ketto (India)"},
    {"id": "milaap", "label": "Milaap (India)"},
    {"id": "mchanga", "label": "M-Changa (Africa)"},
    {"id": "backabuddy", "label": "BackaBuddy (South Africa)"},
    {"id": "giveasia", "label": "Give.asia (Southeast Asia)"},
    {"id": "thundafund", "label": "Thundafund (Africa)"},
    {"id": "justgiving", "label": "JustGiving"},
    {"id": "gogetfunding", "label": "GoGetFunding"},
    {"id": "givebutter", "label": "Givebutter"},
    {"id": "mightycause", "label": "Mightycause"},
    {"id": "chuffed", "label": "Chuffed"},
    {"id": "fundrazr", "label": "FundRazR"},
    {"id": "globalgiving", "label": "GlobalGiving"},
    {"id": "donorbox", "label": "Donorbox"},
    {"id": "patreon", "label": "Patreon"},
]

SUPPORTED_PLATFORM_COUNT = len(PLATFORM_CATALOG)
