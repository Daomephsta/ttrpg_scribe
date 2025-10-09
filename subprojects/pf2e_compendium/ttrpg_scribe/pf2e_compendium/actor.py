from dataclasses import dataclass


@dataclass
class DetailedValue[T]:
    value: T
    details: str
