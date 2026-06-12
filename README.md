# OHFF Teletext

Single-page teletext generator for OHFF Flora & Fauna activations.

This project is based on the generator pattern, EP1 framing, and teletext
character encoding work from Zouppen OH64K's
[`zouppen/bm-teletext`](https://github.com/zouppen/bm-teletext).

Data sources:

- `https://spots.wwff.co/static/spots.json`
- `https://spots.wwff.co/static/agendas.json`

Only references beginning with `OHFF-` are shown.

## Setup

```sh
python3 -m venv .venv
. .venv/bin/activate
pip install -e '.[dev]'
```

## Usage

```sh
ohff-teletext-page json
ohff-teletext-page --time '2026-06-12T13:15:00+00:00' json
ohff-teletext-page teletext --subpage 590/1 page.ep1
ohff-teletext-page html --subpage 590/1 page.html
```

The page first fills `Puskassa nyt!` with spots from the last 30 minutes, then
adds active and forthcoming agenda entries, and finally uses remaining rows for
`Puskassa tänään oli` spots from the current Finnish date that are older than
30 minutes.

All rendered times are Finnish time.

## Preview and EP1 tools

`ylettv-cli` can get and put the same `.ep1` files used here, and its
`ep1_to_rows` helper validates the same 1008-byte shape. The current CLI does
not include a local render command, so `ohff-teletext-page html` renders the
generated EP1 bytes into a browser-viewable preview.

HTML previews embed the public-domain Teletext50 font from
[`glxxyz/bedstead`](https://github.com/glxxyz/bedstead), via
<https://galax.xyz/Teletext50/>.

Example:

```sh
ohff-teletext-page teletext --subpage 590/1 page.ep1
ohff-teletext-page html --subpage 590/1 page.html
```

## Samples

Rendered examples live in `samples/`. Regenerate them with:

```sh
python3 scripts/render_samples.py
```

## Tests

```sh
pytest
```

## License

This project is licensed under GPL-3.0-or-later because it adapts the structure
and EP1 rendering approach from `zouppen/bm-teletext`, which is GPL-3.0.

The bundled Teletext50 font is public domain.

## Credits

Full credit for the original teletext generator structure and EP1 rendering
approach goes to Zouppen OH64K and
[`zouppen/bm-teletext`](https://github.com/zouppen/bm-teletext). This project
adapts the `dmr-teletext` style of that repository for OHFF Flora & Fauna spot
and agenda data.
