"""Seed givefund.db with sample campaigns for local dev when scraping is blocked."""

import asyncio

from db import create_table, get_connection, upsert_campaign

SAMPLE_CAMPAIGNS = [
    {
        "title": "Help Maria beat stage 3 breast cancer",
        "story_snippet": "Maria is a single mother of two facing months of chemo and lost wages while her family covers care and transport.",
        "photo_url": "https://images.unsplash.com/photo-1584515933487-779824d29309?auto=format&fit=crop&w=900&q=80",
        "goal_amount": 45000.0,
        "raised_amount": 12800.0,
        "platform": "gofundme",
        "campaign_url": "https://www.gofundme.com/f/sample-maria-cancer",
        "category": "medical",
        "location": "Chicago, IL",
    },
    {
        "title": "Tuition for Aisha's nursing degree",
        "story_snippet": "Aisha needs help covering her final semester before clinical placement begins this fall.",
        "photo_url": "https://images.unsplash.com/photo-1523050854058-8df90110c9f1?auto=format&fit=crop&w=900&q=80",
        "goal_amount": 8500.0,
        "raised_amount": 7200.0,
        "platform": "launchgood",
        "campaign_url": "https://www.launchgood.com/project/sample-aisha-nursing",
        "category": "education",
        "location": "Detroit, MI",
    },
    {
        "title": "Rebuild after the apartment fire",
        "story_snippet": "Three families lost essentials and need deposits, clothing, and short-term housing after an electrical fire.",
        "photo_url": "https://images.unsplash.com/photo-1518005020951-eccb494ad742?auto=format&fit=crop&w=900&q=80",
        "goal_amount": 22000.0,
        "raised_amount": 9400.0,
        "platform": "fundly",
        "campaign_url": "https://fundly.com/campaign/sample-fire-relief",
        "category": "emergency",
        "location": "Houston, TX",
    },
    {
        "title": "Community garden for Riverside seniors",
        "story_snippet": "Neighbors are raising funds for raised beds, soil, and tools so seniors can grow food together.",
        "photo_url": "https://images.unsplash.com/photo-1416879595882-3373a0488b5b?auto=format&fit=crop&w=900&q=80",
        "goal_amount": 6000.0,
        "raised_amount": 4100.0,
        "platform": "gofundme",
        "campaign_url": "https://www.gofundme.com/f/sample-riverside-garden",
        "category": "community",
        "location": "Portland, OR",
    },
    {
        "title": "Surgery fund for baby Yusuf",
        "story_snippet": "Yusuf was born with a heart defect. His parents need help with surgery and recovery costs.",
        "photo_url": "https://images.unsplash.com/photo-1555252333-9f8e92a85df1?auto=format&fit=crop&w=900&q=80",
        "goal_amount": 35000.0,
        "raised_amount": 28900.0,
        "platform": "launchgood",
        "campaign_url": "https://www.launchgood.com/project/sample-baby-yusuf",
        "category": "medical",
        "location": "Dearborn, MI",
    },
    {
        "title": "Scholarship for first-gen college student",
        "story_snippet": "Daniel was accepted to engineering school and needs help with books, housing, and a laptop.",
        "photo_url": "https://images.unsplash.com/photo-1523240795612-9a054b0db644?auto=format&fit=crop&w=900&q=80",
        "goal_amount": 12000.0,
        "raised_amount": 4800.0,
        "platform": "fundly",
        "campaign_url": "https://fundly.com/campaign/sample-daniel-scholarship",
        "category": "education",
        "location": "Atlanta, GA",
    },
]


async def seed() -> None:
    """Insert sample campaigns for integration testing."""
    async with get_connection() as conn:
        await create_table(conn)
        for campaign in SAMPLE_CAMPAIGNS:
            await upsert_campaign(conn, campaign)
    print(f"Seeded {len(SAMPLE_CAMPAIGNS)} campaigns into DB")


if __name__ == "__main__":
    asyncio.run(seed())
