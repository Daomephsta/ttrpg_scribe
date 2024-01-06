from dataclasses import dataclass
from typing import Any

from dnd_scribe.pf2e_bestiary.actions import Action


@dataclass
class PF2Hazard:
    name: str
    level: int
    notice: int
    disable: str
    actions: list[Action]
    reset: str

    def to_json(self) -> dict[str, Any]:
        return dict(
            name=self.name,
            level=self.level,
            notice=self.notice,
            disable=self.disable,
            actions=self.actions,
            reset=self.reset,
        )

    @classmethod
    def from_json(cls, data):
        return PF2Hazard(
            name=data['name'],
            level=data['level'],
            notice=data['notice'],
            disable=data['disable'],
            actions=[Action.from_json(action) for action in data['actions']],
            reset=data['reset'],
        )
