from dataclasses import dataclass
from typing import Any, Self


@dataclass
class ArmourClass:
    value: int
    desc_format: str

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> Self:
        return cls(data['value'], data['desc_format'])

    def to_json(self) -> dict[str, Any]:
        return dict(value=self.value, desc_format=self.desc_format)

    def desc(self):
        return self.desc_format.format(ac=self.value)

    def __str__(self) -> str:
        return self.desc()
