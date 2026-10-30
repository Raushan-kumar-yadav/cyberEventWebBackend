from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Team
from app.schemas.monitor import LeaderboardRow


# points of teams 
def _rank_key(team: Team) -> tuple[int, bool, int, bool, datetime | None]:
    return (
        -team.points,
        not team.has_reached_delhi,
        team.powerups_used,
        team.reached_delhi_at is None,
        team.reached_delhi_at,
    )


async def ranking(db: AsyncSession) -> list[LeaderboardRow]:
    teams = sorted(await db.scalars(select(Team)), key=lambda t: (_rank_key(t), t.id))
    rows: list[LeaderboardRow] = []
    for position, team in enumerate(teams, start=1):
        tied = position > 1 and _rank_key(teams[position - 2]) == _rank_key(team)
        rows.append(
            LeaderboardRow(
                rank=rows[-1].rank if tied else position,
                team_id=team.id,
                team_name=team.name,
                points=team.points,
                has_reached_delhi=team.has_reached_delhi,
                reached_delhi_at=team.reached_delhi_at,
                powerups_used=team.powerups_used,
                playthroughs=team.playthroughs,
            )
        )
    return rows
