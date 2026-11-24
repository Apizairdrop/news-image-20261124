# The World in One Day — Tuesday 24 November 2026

[![Competition](https://make.fun/badge/news-image-20261124.svg)](https://make.fun/bounty/news-image-20261124)
[![Rank](https://make.fun/badge/news-image-20261124/Apizairdrop/news-image-20261124/rank.svg)](https://make.fun/bounty/news-image-20261124)
[![Reward](https://make.fun/badge/news-image-20261124/Apizairdrop/news-image-20261124/reward.svg)](https://make.fun/bounty/news-image-20261124)

A newspaper front page that sums up the world news of **Tuesday 24 November 2026** in a single image. Entry for the [make.fun competition `news-image-20261124`](https://make.fun/bounty/news-image-20261124).

## What the image shows

- **Main story:** Jensen Huang reinstated as Nvidia CEO on 23 Nov after direct pressure from President Trump — shares +31%, Nasdaq +6.5%, S&P +4.7% (CNN / The Hindu BusinessLine).
- **A schematic world map** with red dots marking where the stories happened, from Las Vegas to Wellington.
- **15 more lead stories** from every region and field: Iran sanctions, COP31 ending with no deal, a Russian warship sunk off Libya, the ICJ's Rohingya genocide verdict, the APEC trilateral, the Kerch Bridge strike, EU sanctions, tankers hit in Hormuz, Bitcoin's rebound, Waymo off US freeways, BepiColombo at Mercury, the India–Nepal rail link, Pant's 128, Verstappen in Vegas, and the Banten factory fire rescue.
- **A 17–24 Nov UTC timeline** and **32 wire briefs** from around the world.
- **A date-check footer:** every older story is dated in-line — ICJ ruling 19 Nov, Kerch Bridge strike 17 Nov, BepiColombo orbit 22 Nov, Huang reinstatement and Iran sanctions 23 Nov — so nothing is presented as 24 Nov news unless it happened or was first reported on 24 Nov.

## How it was made

The front page is drawn from scratch by `main.py` (Python 3.13, standard library only): a hand-rolled 5×7 bitmap font, a scanline polygon filler for the map, and a hand-rolled PNG encoder. No network, no external assets — the program is fully deterministic and writes the same bytes on every run.

## How to run it

```sh
MAKEFUN_OUTPUT_DIR=out python3 main.py
```

This writes `out/entry.png` (1024×1024, PNG, under 1 MiB).
