"""Repair GoFundMe goal_amount values that were stored far below raised totals."""

import asyncio
import logging

from db import get_connection

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _normalize_goal(goal: float, raised: float) -> float:
    """Scale up goals that are implausibly small relative to amount raised."""
    if goal <= 0 or raised <= 0:
        return goal

    adjusted = goal
    for _ in range(4):
        if raised <= adjusted * 1.5:
            break
        if adjusted < 100:
            adjusted *= 100
        elif adjusted < 10_000:
            adjusted *= 10
        else:
            break
    return round(adjusted, 2)


async def fix_goals() -> None:
    """Update understated goals in the local givefund.db."""
    async with get_connection() as conn:
        rows = await conn.execute_fetchall(
            """
            SELECT id, goal_amount, raised_amount
            FROM campaigns
            WHERE platform = 'gofundme'
              AND goal_amount IS NOT NULL
              AND goal_amount > 0
              AND raised_amount IS NOT NULL
              AND raised_amount > 0
            """
        )
        updated = 0
        for row in rows:
            goal = float(row[1])
            raised = float(row[2])
            new_goal = _normalize_goal(goal, raised)
            if new_goal != goal:
                await conn.execute(
                    "UPDATE campaigns SET goal_amount = ? WHERE id = ?",
                    (new_goal, row[0]),
                )
                updated += 1

        await conn.commit()
        logger.info("Fixed %d GoFundMe goal amounts", updated)


if __name__ == "__main__":
    asyncio.run(fix_goals())
