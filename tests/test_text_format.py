from datetime import UTC, datetime

from ohff_teletext.page_data import build_page
from ohff_teletext.text_format import (
    EP1_PAGE_ROWS,
    EP1_PREFIX,
    EP1_SUFFIX,
    LINE_WIDTH,
    decode_teletext_byte,
    ep1_rows,
    format_ep1_html,
    format_page_ep1,
    format_page_html,
    format_page_text,
)


def visible_ep1_row(row: bytes) -> str:
    return "".join(" " if value < 32 else decode_teletext_byte(value) for value in row)


def test_format_page_ep1_is_one_fixed_size_teletext_page() -> None:
    page = build_page(
        spots=[
            {
                "activator": "OH2ÄÄNI/P",
                "frequency_khz": 7038,
                "mode": "CW",
                "reference": "OHFF-2144",
                "reference_name": "Kiimamäen luonnonsuojelualue",
                "spot_time": int(
                    datetime(2026, 6, 12, 13, 4, tzinfo=UTC).timestamp()
                ),
            }
        ],
        agendas=[],
        page_time=datetime(2026, 6, 12, 13, 15, tzinfo=UTC),
    )

    output = format_page_ep1(page, subpage="590/1")

    assert output.startswith(EP1_PREFIX)
    assert output.endswith(EP1_SUFFIX)
    assert len(output) == len(EP1_PREFIX) + EP1_PAGE_ROWS * LINE_WIDTH + len(EP1_SUFFIX)
    assert b"FINNISH FLORA & FAUNA - OHFF.fi" in output
    assert b"OH2[[NI/P" in output


def test_format_page_ep1_uses_corrected_header_and_footer_layout() -> None:
    page = build_page(
        spots=[
            {
                "activator": "OH2ÄÄNI/P",
                "frequency_khz": 7038,
                "mode": "CW",
                "reference": "OHFF-2144",
                "reference_name": "Kiimamäen luonnonsuojelualue",
                "spot_time": int(
                    datetime(2026, 6, 12, 13, 4, tzinfo=UTC).timestamp()
                ),
            }
        ],
        agendas=[],
        page_time=datetime(2026, 6, 12, 13, 15, tzinfo=UTC),
    )

    rows = ep1_rows(format_page_ep1(page, subpage="590/1"))

    assert rows[0] == b" " * LINE_WIDTH
    assert visible_ep1_row(rows[1]) == "    Puskatutka    Päivitetty 16:15 590/1"
    assert visible_ep1_row(rows[2]) == " " * LINE_WIDTH
    assert visible_ep1_row(rows[3]) == "    FINNISH FLORA & FAUNA - OHFF.fi     "
    assert visible_ep1_row(rows[4]) == " " * LINE_WIDTH
    assert visible_ep1_row(rows[5]) == " *  Puskassa nyt!                       "
    assert visible_ep1_row(rows[22]) == " Tiedot: spots.wwff.co                  "
    assert visible_ep1_row(rows[23]) == " Ajat Suomen aikaa (SA)                 "
    assert visible_ep1_row(rows[24]) == " " * LINE_WIDTH


def test_format_page_text_contains_sections_and_footer() -> None:
    page = build_page(
        spots=[],
        agendas=[],
        page_time=datetime(2026, 6, 12, 13, 15, tzinfo=UTC),
    )

    output = format_page_text(page)

    assert "OHFF Flora & Fauna" in output
    assert "Ei OHFF-osumia." in output
    assert "Tiedot: spots.wwff.co / ohff.fi" in output


def test_format_page_html_renders_ep1_bytes_for_viewing() -> None:
    page = build_page(
        spots=[
            {
                "activator": "OH2ÄÄNI/P",
                "frequency_khz": 7038,
                "mode": "CW",
                "reference": "OHFF-2144",
                "reference_name": "Kiimamäen luonnonsuojelualue",
                "spot_time": int(
                    datetime(2026, 6, 12, 13, 4, tzinfo=UTC).timestamp()
                ),
            }
        ],
        agendas=[],
        page_time=datetime(2026, 6, 12, 13, 15, tzinfo=UTC),
    )

    output = format_page_html(page, subpage="590/1")

    assert '<pre class="teletext">' in output
    assert "OH2ÄÄNI/P" in output
    assert "OHFF-2144" in output


def test_format_ep1_html_validates_ep1_shape() -> None:
    try:
        format_ep1_html(b"bad")
    except ValueError as exc:
        assert "1008 bytes" in str(exc)
    else:
        raise AssertionError("format_ep1_html accepted invalid EP1 data")
