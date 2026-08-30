from collections.abc import Sequence

from sqlalchemy import select

from app.db.models import AlertChannelModel
from app.db.repos._base import BaseRepo


class AlertChannelRepo(BaseRepo[AlertChannelModel]):
    model = AlertChannelModel

    async def notifiable(self, address: str) -> Sequence[AlertChannelModel]:
        stmt = select(AlertChannelModel).where(
            AlertChannelModel.address == address,
            AlertChannelModel.enabled.is_(True),
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def invitable(self, addresses: list[str], lang: str) -> list[AlertChannelModel]:
        stmt = select(AlertChannelModel).where(
            AlertChannelModel.address.in_(addresses),
            AlertChannelModel.invite_link.is_not(None),
            AlertChannelModel.enabled.is_(True),
        )
        result = await self.session.execute(stmt)
        best: dict[str, AlertChannelModel] = {}
        for channel in result.scalars().all():
            if channel.address is None:
                continue
            current = best.get(channel.address)
            if current is None or _match(channel.lang, lang) < _match(current.lang, lang):
                best[channel.address] = channel
        return list(best.values())


# One channel per address: the reader's own language wins, English is the fallback,
# and anything else is better than hiding the channel altogether.
def _match(lang: str, wanted: str) -> int:
    if lang == wanted:
        return 0
    return 1 if lang == "en" else 2
