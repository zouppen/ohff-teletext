from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any, Literal, TypedDict
from zoneinfo import ZoneInfo


FINLAND = ZoneInfo("Europe/Helsinki")
REFERENCE_PREFIX = "OHFF-"
RECENT_SPOT_WINDOW = timedelta(minutes=30)
BODY_ROW_LIMIT = 20


class SpotEntry(TypedDict):
    type: Literal["spot"]
    section: Literal["now", "today"]
    activator: str
    frequency_khz: str
    mode: str
    reference: str
    reference_name: str
    spot_time: str


class AgendaEntry(TypedDict):
    type: Literal["agenda"]
    section: Literal["agenda"]
    activator: str
    reference: str
    utc_start: str
    utc_end: str
    band: str
    mode: str
    remarks: str
    state: Literal["active", "later"]


class SectionEntry(TypedDict):
    type: Literal["section"]
    title: str


class MessageEntry(TypedDict):
    type: Literal["message"]
    text: str


PageEntry = SpotEntry | AgendaEntry | SectionEntry | MessageEntry


class PageData(TypedDict):
    page_time: str
    timezone: str
    body_row_limit: int
    now_spot_count: int
    agenda_count: int
    today_spot_count: int
    entries: list[PageEntry]


def parse_unix_timestamp(value: Any) -> datetime | None:
    try:
        return datetime.fromtimestamp(float(value), UTC)
    except (TypeError, ValueError, OSError):
        return None


def parse_utc_datetime(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def clean_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def is_ohff_reference(value: Any) -> bool:
    return clean_text(value).upper().startswith(REFERENCE_PREFIX)


def spot_entry(raw: dict[str, Any], section: Literal["now", "today"]) -> SpotEntry | None:
    spot_time = parse_unix_timestamp(raw.get("spot_time"))
    if spot_time is None or not is_ohff_reference(raw.get("reference")):
        return None
    return {
        "type": "spot",
        "section": section,
        "activator": clean_text(raw.get("activator")),
        "frequency_khz": format_frequency(raw.get("frequency_khz")),
        "mode": clean_text(raw.get("mode")).upper(),
        "reference": clean_text(raw.get("reference")).upper(),
        "reference_name": clean_text(raw.get("reference_name")),
        "spot_time": spot_time.isoformat(),
    }


def agenda_entry(raw: dict[str, Any], now: datetime) -> AgendaEntry | None:
    if not is_ohff_reference(raw.get("reference")):
        return None
    start = parse_utc_datetime(raw.get("utc_start"))
    end = parse_utc_datetime(raw.get("utc_end"))
    if start is None or end is None:
        return None
    if end < now:
        return None
    return {
        "type": "agenda",
        "section": "agenda",
        "activator": clean_text(raw.get("activator_call")),
        "reference": clean_text(raw.get("reference")).upper(),
        "utc_start": start.isoformat(),
        "utc_end": end.isoformat(),
        "band": clean_text(raw.get("band")),
        "mode": clean_text(raw.get("mode")),
        "remarks": clean_text(raw.get("remarks")),
        "state": "active" if start <= now <= end else "later",
    }


def format_frequency(value: Any) -> str:
    try:
        frequency = float(value)
    except (TypeError, ValueError):
        return ""
    if frequency.is_integer():
        return str(int(frequency))
    return f"{frequency:.1f}".rstrip("0").rstrip(".")


def local_date(value: datetime) -> datetime.date:
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(FINLAND).date()


def entry_row_cost(entry: PageEntry) -> int:
    if entry["type"] == "section":
        return 2
    return 1


def add_section_entries(
    entries: list[PageEntry],
    candidates: list[PageEntry],
    title: str,
    remaining_rows: int,
) -> tuple[int, int]:
    if not candidates or remaining_rows < 3:
        return remaining_rows, 0

    used = 1
    selected: list[PageEntry] = [{"type": "section", "title": title}]
    for candidate in candidates:
        cost = entry_row_cost(candidate)
        if used + cost > remaining_rows:
            break
        selected.append(candidate)
        used += cost

    if len(selected) == 1:
        return remaining_rows, 0

    entries.extend(selected)
    return remaining_rows - used, len(selected) - 1


def build_page(
    spots: list[dict[str, Any]],
    agendas: list[dict[str, Any]],
    page_time: datetime | None = None,
    body_row_limit: int = BODY_ROW_LIMIT,
) -> PageData:
    now = (page_time or datetime.now(UTC)).astimezone(UTC)
    today = local_date(now)
    recent_cutoff = now - RECENT_SPOT_WINDOW

    ohff_spots = [
        (spot_time, raw)
        for raw in spots
        if (spot_time := parse_unix_timestamp(raw.get("spot_time"))) is not None
        and is_ohff_reference(raw.get("reference"))
    ]
    ohff_spots.sort(key=lambda item: item[0], reverse=True)

    now_spots = [
        entry
        for spot_time, raw in ohff_spots
        if recent_cutoff <= spot_time <= now
        if (entry := spot_entry(raw, "now")) is not None
    ]
    today_spots = [
        entry
        for spot_time, raw in ohff_spots
        if spot_time < recent_cutoff and local_date(spot_time) == today
        if (entry := spot_entry(raw, "today")) is not None
    ]

    agenda_entries = [
        entry
        for raw in agendas
        if (entry := agenda_entry(raw, now)) is not None
    ]
    agenda_entries.sort(
        key=lambda entry: (
            0 if entry["state"] == "active" else 1,
            datetime.fromisoformat(entry["utc_start"]),
            entry["activator"],
        )
    )

    entries: list[PageEntry] = []
    remaining = body_row_limit
    remaining, now_count = add_section_entries(
        entries,
        now_spots,
        "Puskassa nyt!",
        remaining,
    )
    remaining, agenda_count = add_section_entries(
        entries,
        agenda_entries,
        "Agendalla ..",
        remaining,
    )
    remaining, today_count = add_section_entries(
        entries,
        today_spots,
        "Puskassa tänään oli",
        remaining,
    )
    if not entries:
        entries.append({"type": "message", "text": "Ei OHFF-osumia."})

    return {
        "page_time": now.isoformat(),
        "timezone": "Europe/Helsinki",
        "body_row_limit": body_row_limit,
        "now_spot_count": now_count,
        "agenda_count": agenda_count,
        "today_spot_count": today_count,
        "entries": entries,
    }
