from collections import defaultdict
from collections.abc import Iterator
from typing import Any

from sqlalchemy import select, tuple_, update

from app.bags import SlotState, bag_state, slot_state
from app.db.models import BagModel, BagSlotModel, ProviderModel
from app.db.repos._base import BaseRepo
from app.utils import utcnow

CHUNK = 100


def _chunks(keys: list[Any]) -> Iterator[list[Any]]:
    for offset in range(0, len(keys), CHUNK):
        yield keys[offset : offset + CHUNK]


class StateRepo(BaseRepo[BagSlotModel]):
    model = BagSlotModel

    # States age with the clock, so the whole picture is rebuilt at once rather than
    # patched per row: loading and computing costs about 110 ms on 13k slots, and only
    # the rows whose verdict changed are written back.
    async def refresh(self) -> tuple[int, int]:
        slots = (await self.session.execute(select(BagSlotModel))).scalars().all()
        bags = {bag.address: bag for bag in (await self.session.execute(select(BagModel))).scalars().all()}
        providers = {p.pubkey: p for p in (await self.session.execute(select(ProviderModel))).scalars().all()}

        peers: dict[str, int] = defaultdict(int)
        proved: dict[str, int] = defaultdict(int)
        for slot in slots:
            peers[slot.address] += 1
            proved[slot.address] += slot.last_proof_at is not None

        now = utcnow()
        by_bag: dict[str, list[SlotState]] = defaultdict(list)
        slot_moves: dict[str, list[tuple[str, str]]] = defaultdict(list)
        for slot in slots:
            bag = bags.get(slot.address)
            if bag is None:
                continue
            state = slot_state(
                slot, bag, providers.get(slot.provider_pubkey), peers[slot.address], proved[slot.address], now
            )
            by_bag[slot.address].append(state)
            if slot.state != state.value:
                slot_moves[state.value].append((slot.address, slot.provider_pubkey))

        bag_moves: dict[str, list[str]] = defaultdict(list)
        for address, bag in bags.items():
            rolled = bag_state(bag, by_bag.get(address, []))
            if bag.state != rolled.value:
                bag_moves[rolled.value].append(address)

        # One statement per state, not per row: eight states against thousands of rows, and
        # the first pass after a migration moves every one of them.
        for state_value, keys in slot_moves.items():
            for chunk in _chunks(keys):
                await self.session.execute(
                    update(BagSlotModel)
                    .where(tuple_(BagSlotModel.address, BagSlotModel.provider_pubkey).in_(chunk))
                    .values(state=state_value)
                    .execution_options(synchronize_session=False)
                )
        for state_value, addresses in bag_moves.items():
            for chunk in _chunks(addresses):
                await self.session.execute(
                    update(BagModel)
                    .where(BagModel.address.in_(chunk))
                    .values(state=state_value)
                    .execution_options(synchronize_session=False)
                )
        return sum(len(keys) for keys in slot_moves.values()), sum(len(keys) for keys in bag_moves.values())
