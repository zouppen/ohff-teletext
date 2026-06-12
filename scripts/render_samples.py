from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ohff_teletext.page_data import build_page  # noqa: E402
from ohff_teletext.text_format import format_page_html  # noqa: E402


PAGE_TIME = datetime(2026, 6, 12, 13, 15, tzinfo=UTC)
SUBPAGE = "590/1"
SAMPLES_DIR = ROOT / "samples"


def spot(
    activator: str,
    reference: str,
    minutes_ago: int,
    frequency_khz: float,
    mode: str,
    name: str = "Kansallispuisto",
) -> dict:
    return {
        "activator": activator,
        "frequency_khz": frequency_khz,
        "mode": mode,
        "reference": reference,
        "reference_name": name,
        "spot_time": int((PAGE_TIME - timedelta(minutes=minutes_ago)).timestamp()),
    }


def agenda(
    activator: str,
    reference: str,
    start: str,
    end: str,
    band: str,
    mode: str,
    remarks: str = "",
) -> dict:
    return {
        "activator_call": activator,
        "reference": reference,
        "utc_start": start,
        "utc_end": end,
        "band": band,
        "mode": mode,
        "remarks": remarks,
    }


def sample_data() -> dict[str, tuple[list[dict], list[dict]]]:
    recent_spots = [
        spot(
            "OH1ABC",
            "OHFF-0025",
            8,
            14074,
            "SSB",
            "Aakkosten kansallispuisto",
        ),
        spot(
            "OH2XYZ",
            "OHFF-0040",
            18,
            14230,
            "SSB",
            "Nuuksion kansallispuisto",
        ),
    ]
    previous_spots = [
        spot(
            "OH8UV/P",
            "OHFF-1985",
            95,
            7032,
            "CW",
            "Päätyvaaran luonnonsuojelualue",
        ),
        spot(
            "OH1NYZ/P",
            "OHFF-0025",
            210,
            18144,
            "SSB",
            "Aakkosten kansallispuisto",
        ),
        spot(
            "OH6LAKE/P",
            "OHFF-0777",
            315,
            10118,
            "CW",
            "Järvenrannan luonnonsuojelualue",
        ),
    ]
    future_agendas = [
        agenda(
            "OH2ABC/P",
            "OHFF-0030",
            "2026-06-12 12:30:00",
            "2026-06-12 14:15:00",
            "40m, 20m",
            "SSB, CW",
            "Aktiivinen tänään",
        ),
        agenda(
            "OH4FOX/P",
            "OHFF-0444",
            "2026-06-12 14:30:00",
            "2026-06-12 16:30:00",
            "80m, 40m, 20m",
            "SSB",
            "Illalla äänessä",
        ),
        agenda(
            "OH6TREE/P",
            "OHFF-1200",
            "2026-06-13 08:00:00",
            "2026-06-13 10:00:00",
            "40m, 30m, 20m",
            "CW",
            "Huomenna",
        ),
    ]
    return {
        "01-full-mixed.html": (recent_spots + previous_spots[:2], future_agendas),
        "02-no-data.html": ([], []),
        "03-agendas-only.html": ([], future_agendas),
        "04-previous-activations-today.html": (previous_spots, []),
        "05-recent-spots-no-agendas.html": (recent_spots, []),
    }


def render_samples() -> list[Path]:
    SAMPLES_DIR.mkdir(exist_ok=True)
    rendered: list[Path] = []
    for filename, (spots, agendas) in sample_data().items():
        page = build_page(spots, agendas, page_time=PAGE_TIME)
        output_path = SAMPLES_DIR / filename
        output_path.write_text(
            format_page_html(page, subpage=SUBPAGE),
            encoding="utf-8",
        )
        rendered.append(output_path)
    return rendered


def main() -> int:
    for path in render_samples():
        print(path.relative_to(ROOT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
