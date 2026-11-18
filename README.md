# The World in One Day — news-image-20261118

An entry for make.fun's **news-image-20261118** ("Sum up 18 November's
world news in one image"). `main.py` draws a newspaper-style front page
that sums up the world news of **Wednesday 18 November 2026** and
writes it to `entry.png` (1024x768 PNG, ~13.5 KB).

The page carries a masthead naming the day, one lead story (US strikes
an Iran missile site on Qeshm; Iran fires drones at Bahrain and Kuwait
in reply) and eight story panels spanning the day's summit in Shenzhen,
Voyager 1 reaching one light-day, the US losing measles-free status,
the Congo Ebola outbreak, the Alaska Senate flip, the Kerch Bridge
strike, the Siberian plane crash and Cyclone Xavier — with small drawn
icons (globe, rocket, ballot box, storm swirl). No photographs: every
pixel is drawn by the program.

## How it works

- `main.py` — Python 3, standard library only. It implements its own
  PNG encoder (zlib + struct + CRC), an RGB framebuffer, drawing
  primitives (rectangles, lines, circles, ellipses) and a 5x7 bitmap
  font with scaling and word wrap. No clock, no randomness, no
  network: two runs write byte-identical output.
- The program writes to `MAKEFUN_OUTPUT_DIR` when set (development)
  and to `/output` otherwise (production), as the competition's
  harness expects.
- `entry.png` — the rendered page, committed so the result can be
  inspected without running anything.
- `SOURCES.md` — the day's stories and the real news roundups they
  were researched from.
- `tests/test_entry.py` — standard-library unittest: runs the program
  twice and asserts byte-identical output, a valid PNG signature,
  IHDR dimensions within 1024x1024, size within 1 MiB, and an IDAT
  stream that zlib-decompresses to the described scanlines.

## Run it

```sh
mkdir -p out && MAKEFUN_OUTPUT_DIR=out python3 main.py
python3 tests/test_entry.py
```

## Status

This is an **initial draft, pending team review** (JEMBOER → MUSE →
independent review). It has not been submitted. The headlines are the
stories as reported during 18 November 2026; before any final
submission the set should be refreshed against the day's settled
reporting (see the refresh note in `SOURCES.md`).
