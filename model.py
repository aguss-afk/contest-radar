"""Normalized contest model shared by every source adapter."""

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(slots=True)
class Contest:
    key: str
    site: str
    title: str
    url: str
    start: int
    end: int
    duration: int
    kind: str = "contest"
    note: str = ""
    rated: bool | None = None

    def to_dict(self) -> dict:
        data = asdict(self)
        data["duration"] = max(0, int(data["duration"]))
        data["start"] = int(data["start"])
        data["end"] = int(data["end"])
        return data
