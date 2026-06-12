from __future__ import annotations

import base64
from datetime import UTC, datetime
from html import escape
from importlib import resources
from typing import Iterable

from ohff_teletext.page_data import AgendaEntry, FINLAND, PageData, PageEntry, SpotEntry


LINE_WIDTH = 40
EP1_PREFIX = b"\xfe\x01\x18\x00\x00\x00"
EP1_SUFFIX = b"\x00\x00"
EP1_PAGE_ROWS = 25
EP1_HEADER_ROWS = 2
EP1_FOOTER_ROWS = 2
EP1_BODY_ROWS = EP1_PAGE_ROWS - EP1_HEADER_ROWS - EP1_FOOTER_ROWS

COLOUR_RED = b"\x01"
COLOUR_GREEN = b"\x02"
COLOUR_YELLOW = b"\x03"
COLOUR_BLUE = b"\x04"
COLOUR_CYAN = b"\x06"
COLOUR_WHITE = b"\x07"
BLACK_BACKGROUND = 0x1C
NEW_BACKGROUND = 0x1D

HTML_FOREGROUND_COLOURS = {
    0: "#000",
    1: "#ff4b22",
    2: "#35c759",
    3: "#ffc400",
    4: "#aeb8c6",
    5: "#ff4fd8",
    6: "#64d8ff",
    7: "#f2f2f2",
}

HTML_BACKGROUND_COLOURS = {
    **HTML_FOREGROUND_COLOURS,
    4: "#0c4594",
}


def format_page_text(page: PageData) -> str:
    page_time = local_time(page["page_time"])
    rows = [
        "OHFF Flora & Fauna",
        f"Päivitetty {page_time.strftime('%H:%M')}",
        "",
        *format_body_text(page["entries"], page_time),
        "Tiedot: spots.wwff.co / ohff.fi",
        "Ajat Suomen aikaa (SA)",
    ]
    return "\n".join(row[:LINE_WIDTH] for row in rows)


def format_page_ep1(page: PageData, subpage: str) -> bytes:
    page_time = local_time(page["page_time"])
    rows = [
        ep1_row(
            b" "
            + COLOUR_YELLOW
            + encode_teletext("OHFF", 8)
            + COLOUR_BLUE
            + b"P{ivitetty "
            + page_time.strftime("%H:%M").encode("ascii")
            + b" "
            + COLOUR_WHITE
            + encode_teletext(subpage, 6, align=">")
        ),
        ep1_row(
            COLOUR_BLUE
            + bytes([NEW_BACKGROUND])
            + COLOUR_WHITE
            + encode_teletext(" FINNISH FLORA & FAUNA - OHFF.fi", LINE_WIDTH - 3)
        ),
    ]
    body_rows = list(format_body_ep1(page["entries"], page_time))[:EP1_BODY_ROWS]
    rows.extend(body_rows)
    rows.extend([b" " * LINE_WIDTH] * (EP1_BODY_ROWS - len(body_rows)))
    rows.extend(
        [
            ep1_row(COLOUR_CYAN + b"Tiedot: spots.wwff.co"),
            ep1_row(COLOUR_CYAN + b"Ajat Suomen aikaa (SA)"),
        ]
    )
    return EP1_PREFIX + b"".join(rows) + EP1_SUFFIX


def format_page_html(page: PageData, subpage: str) -> str:
    return format_ep1_html(
        format_page_ep1(page, subpage),
        title=f"OHFF Flora & Fauna {subpage}",
    )


def format_ep1_html(ep1_data: bytes, title: str = "Teletext preview") -> str:
    rows = ep1_rows(ep1_data)
    rendered_rows = "\n".join(render_ep1_row_html(row) for row in rows)
    font_face = teletext_font_face_css()
    return f"""<!doctype html>
<html lang="fi">
<head>
  <meta charset="utf-8">
  <title>{escape(title)}</title>
  <style>
    {font_face}
    body {{
      margin: 0;
      min-height: 100vh;
      display: grid;
      place-items: center;
      background: #222;
    }}
    .teletext {{
      box-sizing: content-box;
      width: 40ch;
      margin: 24px;
      padding: 16px;
      background: #000;
      color: #f2f2f2;
      font-family: "Teletext50", Bedstead, "ModeSeven", "European Teletext", monospace;
      font-size: 28px;
      line-height: 1;
      font-weight: 400;
      letter-spacing: 0;
      white-space: pre;
      font-variant-ligatures: none;
      font-synthesis: none;
      text-rendering: geometricPrecision;
      box-shadow: 0 12px 40px rgb(0 0 0 / 0.45);
    }}
  </style>
</head>
<body>
<pre class="teletext">{rendered_rows}</pre>
</body>
</html>
"""


def teletext_font_face_css() -> str:
    try:
        font_bytes = resources.files("ohff_teletext").joinpath(
            "assets/Teletext50.otf"
        ).read_bytes()
    except (FileNotFoundError, ModuleNotFoundError):
        return ""
    encoded = base64.b64encode(font_bytes).decode("ascii")
    return (
        '@font-face { font-family: "Teletext50"; '
        f"src: url(data:font/otf;base64,{encoded}) format('opentype'); "
        "font-weight: 400; font-style: normal; }"
    )


def ep1_rows(ep1_data: bytes) -> list[bytes]:
    expected = len(EP1_PREFIX) + EP1_PAGE_ROWS * LINE_WIDTH + len(EP1_SUFFIX)
    if len(ep1_data) != expected:
        raise ValueError(f"EP1 data must be exactly {expected} bytes")
    if not ep1_data.startswith(EP1_PREFIX):
        raise ValueError("EP1 data has an unexpected prefix")
    if not ep1_data.endswith(EP1_SUFFIX):
        raise ValueError("EP1 data has an unexpected suffix")
    body = ep1_data[len(EP1_PREFIX) : -len(EP1_SUFFIX)]
    return [body[index : index + LINE_WIDTH] for index in range(0, len(body), LINE_WIDTH)]


def render_ep1_row_html(row: bytes) -> str:
    colour = 7
    background = 0
    output: list[str] = []
    run: list[str] = []
    run_colour = colour
    run_background = background

    def flush() -> None:
        nonlocal run_colour, run_background
        if not run:
            return
        output.append(render_html_cell("".join(run), run_colour, run_background))
        run.clear()
        run_colour = colour
        run_background = background

    for value in row:
        if value in HTML_FOREGROUND_COLOURS:
            flush()
            colour = value
            run_colour = colour
            run_background = background
            run.append(" ")
            continue
        if value == NEW_BACKGROUND:
            flush()
            background = colour
            run_colour = colour
            run_background = background
            run.append(" ")
            continue
        if value == BLACK_BACKGROUND:
            flush()
            background = 0
            run_colour = colour
            run_background = background
            run.append(" ")
            continue
        if value < 32:
            run.append(" ")
            continue
        run.append(decode_teletext_byte(value))
    flush()
    return "".join(output)


def render_html_cell(value: str, colour: int, background: int) -> str:
    return (
        f'<span style="color:{HTML_FOREGROUND_COLOURS[colour]};'
        f'background:{HTML_BACKGROUND_COLOURS[background]}">{escape(value)}</span>'
    )


def decode_teletext_byte(value: int) -> str:
    return chr(value).translate(
        str.maketrans(
            {
                "[": "Ä",
                "\\": "Ö",
                "]": "Å",
                "{": "ä",
                "|": "ö",
                "}": "å",
            }
        )
    )


def format_body_text(entries: Iterable[PageEntry], page_time: datetime) -> list[str]:
    rows: list[str] = []
    for entry in entries:
        rows.extend(format_entry_text(entry, page_time))
    return rows


def format_entry_text(entry: PageEntry, page_time: datetime) -> list[str]:
    if entry["type"] == "section":
        return ["", f"* {entry['title']}"]
    if entry["type"] == "message":
        return [entry["text"]]
    if entry["type"] == "spot":
        return format_spot_text(entry)
    return format_agenda_text(entry, page_time)


def format_spot_text(entry: SpotEntry) -> list[str]:
    return [fit(compact_join(spot_parts(entry)))]


def format_agenda_text(entry: AgendaEntry, page_time: datetime) -> list[str]:
    start = local_time(entry["utc_start"])
    return [fit(compact_join(agenda_parts(entry, start, page_time)))]


def format_body_ep1(entries: Iterable[PageEntry], page_time: datetime) -> list[bytes]:
    rows: list[bytes] = []
    for entry in entries:
        rows.extend(format_entry_ep1(entry, page_time))
    return rows


def format_entry_ep1(entry: PageEntry, page_time: datetime) -> list[bytes]:
    if entry["type"] == "section":
        return [
            ep1_row(b" " * LINE_WIDTH),
            ep1_row(
                b" "
                + COLOUR_YELLOW
                + b"* "
                + COLOUR_WHITE
                + encode_teletext(entry["title"], LINE_WIDTH - 3, align="<")
            )
        ]
    if entry["type"] == "message":
        return [ep1_row(b" " + COLOUR_WHITE + encode_teletext(entry["text"], 38))]
    if entry["type"] == "spot":
        return format_spot_ep1(entry)
    return format_agenda_ep1(entry, page_time)


def format_spot_ep1(entry: SpotEntry) -> list[bytes]:
    frequency, mode, activator, reference = spot_parts(entry)
    frequency_width = 12 if entry["section"] == "today" else 10
    activator_width = 8 if entry["section"] == "today" else 9
    return [
        ep1_row(
            b" "
            + COLOUR_YELLOW
            + encode_teletext(frequency, frequency_width, align="<")
            + COLOUR_YELLOW
            + encode_teletext(mode, 4, align="<")
            + COLOUR_WHITE
            + encode_teletext(activator, activator_width, align="<")
            + COLOUR_BLUE
            + encode_teletext(reference, 9, align="<")
        )
    ]


def format_agenda_ep1(entry: AgendaEntry, page_time: datetime) -> list[bytes]:
    start = local_time(entry["utc_start"])
    start_text, activator, reference, details = agenda_parts(entry, start, page_time)
    is_future_day = "." in start_text
    start_width = 7 if is_future_day else 6
    activator_width = 9 if is_future_day else 8
    detail_width = 35 - start_width - activator_width - 9
    return [
        ep1_row(
            b" "
            + COLOUR_YELLOW
            + encode_teletext(start_text, start_width, align="<")
            + COLOUR_WHITE
            + encode_teletext(activator, activator_width, align="<")
            + COLOUR_BLUE
            + encode_teletext(reference, 9, align="<")
            + COLOUR_YELLOW
            + encode_teletext(details, detail_width, align="<")
        )
    ]


def spot_parts(entry: SpotEntry) -> list[str]:
    frequency = with_suffix(entry["frequency_khz"], " kHz")
    if entry["section"] == "today":
        frequency = compact_join(
            [
                local_time(entry["spot_time"]).strftime("%H:%M"),
                with_suffix(entry["frequency_khz"], "k"),
            ]
        )
    return [frequency, entry["mode"], entry["activator"], entry["reference"]]


def agenda_parts(
    entry: AgendaEntry,
    start: datetime,
    page_time: datetime,
) -> list[str]:
    start_text = agenda_start_text(start, page_time)
    details = compact_join([short_modes(entry["mode"]), short_bands(entry["band"])])
    return [start_text, entry["activator"], entry["reference"], details]


def agenda_start_text(start: datetime, page_time: datetime) -> str:
    if start.date() == page_time.astimezone(FINLAND).date():
        return start.strftime("%H:%M")
    return f"{start.day}.{start.month} {start:%H}"


def local_time(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(FINLAND)


def ep1_row(value: bytes) -> bytes:
    return value[:LINE_WIDTH].ljust(LINE_WIDTH, b" ")


def encode_teletext(value: str, width: int, align: str = "<") -> bytes:
    translated = value.translate(
        str.maketrans(
            {
                "Ä": "[",
                "Ö": "\\",
                "Å": "]",
                "ä": "{",
                "ö": "|",
                "å": "}",
            }
        )
    ).encode("ascii", errors="replace")
    translated = translated[:width]
    return f"{translated.decode('ascii'):{align}{width}}".encode("ascii")


def compact_join(parts: list[str]) -> str:
    return " ".join(part for part in parts if part)


def with_suffix(value: str, suffix: str) -> str:
    if not value:
        return ""
    return value + suffix


def short_modes(value: str) -> str:
    if not value:
        return ""
    return value.replace(", ", "/")


def short_bands(value: str) -> str:
    if not value:
        return ""
    return value.replace("m", "").replace(", ", "/")


def fit(value: str) -> str:
    if len(value) <= LINE_WIDTH:
        return value
    return value[: LINE_WIDTH - 1] + ">"
