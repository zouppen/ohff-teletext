from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from ohff_teletext.feeds import AGENDAS_URL, SPOTS_URL, fetch_agendas, fetch_spots
from ohff_teletext.page_data import BODY_ROW_LIMIT, build_page
from ohff_teletext.text_format import format_page_ep1, format_page_html


@dataclass(frozen=True)
class CliOptions:
    output_format: str
    page_time: str | None
    body_rows: int
    subpage: str | None
    output_file: str | None
    spots_url: str
    agendas_url: str


class CliArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        usage = self.format_usage().strip()
        raise ValueError(f"{usage}\n{self.prog}: error: {message}")


def positive_int(value: str) -> int:
    try:
        parsed = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError("must be a positive integer")
    if parsed <= 0:
        raise argparse.ArgumentTypeError("must be a positive integer")
    return parsed


def subpage_text(value: str) -> str:
    if len(value) != 5:
        raise argparse.ArgumentTypeError("must be exactly 5 characters")
    return value


def create_argument_parser() -> argparse.ArgumentParser:
    parser = CliArgumentParser(prog="ohff-teletext-page")
    parser.add_argument("--time", dest="page_time")
    parser.add_argument("--spots-url", default=SPOTS_URL)
    parser.add_argument("--agendas-url", default=AGENDAS_URL)
    subparsers = parser.add_subparsers(
        dest="output_format",
        required=True,
        parser_class=CliArgumentParser,
    )

    json_parser = subparsers.add_parser("json")
    json_parser.add_argument("--body-rows", type=positive_int, default=BODY_ROW_LIMIT)

    teletext_parser = subparsers.add_parser("teletext")
    teletext_parser.set_defaults(body_rows=BODY_ROW_LIMIT)
    teletext_parser.add_argument("--subpage", type=subpage_text, required=True)
    teletext_parser.add_argument("output_file")

    html_parser = subparsers.add_parser("html")
    html_parser.set_defaults(body_rows=BODY_ROW_LIMIT)
    html_parser.add_argument("--subpage", type=subpage_text, required=True)
    html_parser.add_argument("output_file")

    return parser


def parse_cli_options(argv: list[str]) -> CliOptions:
    namespace = create_argument_parser().parse_args(argv)
    return CliOptions(
        output_format=namespace.output_format,
        page_time=namespace.page_time,
        body_rows=namespace.body_rows,
        subpage=getattr(namespace, "subpage", None),
        output_file=getattr(namespace, "output_file", None),
        spots_url=namespace.spots_url,
        agendas_url=namespace.agendas_url,
    )


def parse_page_time(value: str | None) -> datetime:
    if value is None:
        return datetime.now(UTC)
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise ValueError("--time must be an ISO datetime") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    try:
        options = parse_cli_options(argv)
        page_time = parse_page_time(options.page_time)
        spots = fetch_spots(options.spots_url)
        agendas = fetch_agendas(options.agendas_url)
    except (OSError, ValueError) as exc:
        print(exc, file=sys.stderr)
        return 2

    page = build_page(
        spots,
        agendas,
        page_time=page_time,
        body_row_limit=options.body_rows,
    )
    if options.output_format == "teletext":
        Path(options.output_file or "").write_bytes(
            format_page_ep1(page, subpage=options.subpage or "")
        )
    elif options.output_format == "html":
        Path(options.output_file or "").write_text(
            format_page_html(page, subpage=options.subpage or ""),
            encoding="utf-8",
        )
    else:
        print(json.dumps(page, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
