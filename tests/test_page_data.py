from datetime import UTC, datetime

from ohff_teletext.page_data import build_page


NOW = datetime(2026, 6, 12, 13, 15, tzinfo=UTC)


def spot(
    activator: str,
    reference: str,
    minute: int,
    hour: int = 13,
    frequency_khz: float = 14074,
    mode: str = "SSB",
) -> dict:
    return {
        "activator": activator,
        "frequency_khz": frequency_khz,
        "mode": mode,
        "reference": reference,
        "reference_name": "Kansallispuisto",
        "spot_time": int(datetime(2026, 6, 12, hour, minute, tzinfo=UTC).timestamp()),
    }


def agenda(
    activator: str,
    reference: str,
    start: str,
    end: str,
) -> dict:
    return {
        "activator_call": activator,
        "reference": reference,
        "utc_start": start,
        "utc_end": end,
        "band": "40m, 20m",
        "mode": "SSB, CW",
        "remarks": "",
    }


def test_build_page_prioritizes_recent_spots_then_agendas_then_old_today() -> None:
    page = build_page(
        spots=[
            spot("OH1NOW", "OHFF-0001", 10),
            spot("OH2OLD", "OHFF-0002", 30, hour=12),
            spot("SM1NO", "SMFF-0001", 14),
        ],
        agendas=[
            agenda(
                "OH3ACT/P",
                "OHFF-0003",
                "2026-06-12 13:00:00",
                "2026-06-12 14:00:00",
            ),
            agenda(
                "OH4LATER/P",
                "OHFF-0004",
                "2026-06-12 15:00:00",
                "2026-06-12 17:00:00",
            ),
        ],
        page_time=NOW,
        body_row_limit=20,
    )

    assert [entry["type"] for entry in page["entries"]] == [
        "section",
        "spot",
        "section",
        "agenda",
        "agenda",
        "section",
        "spot",
    ]
    assert page["now_spot_count"] == 1
    assert page["agenda_count"] == 2
    assert page["today_spot_count"] == 1


def test_build_page_uses_row_budget() -> None:
    page = build_page(
        spots=[
            spot("OH1A", "OHFF-0001", 14),
            spot("OH2B", "OHFF-0002", 13),
            spot("OH3C", "OHFF-0003", 12),
        ],
        agendas=[
            agenda(
                "OH4D/P",
                "OHFF-0004",
                "2026-06-12 15:00:00",
                "2026-06-12 17:00:00",
            ),
        ],
        page_time=NOW,
        body_row_limit=5,
    )

    assert [entry.get("activator") for entry in page["entries"] if entry["type"] == "spot"] == [
        "OH1A",
        "OH2B",
        "OH3C",
    ]
    assert page["agenda_count"] == 0
