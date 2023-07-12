from dataclasses import dataclass
from typing import Any, Self


@dataclass
class ArmourClass:
    value: int
    desc: str

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> Self:
        return cls(data['value'], data['desc'])

    def to_json(self) -> dict[str, Any]:
        return dict(value=self.value, desc=self.desc)

    def __str__(self) -> str:
        return self.desc