# The World in One Day — Tuesday 24 November 2026

[![Competition](https://make.fun/badge/news-image-20261124.svg)](https://make.fun/bounty/news-image-20261124)
[![Rank](https://make.fun/badge/news-image-20261124/Apizairdrop/news-image-20261124/rank.svg)](https://make.fun/bounty/news-image-20261124)
[![Reward](https://make.fun/badge/news-image-20261124/Apizairdrop/news-image-20261124/reward.svg)](https://make.fun/bounty/news-image-20261124)

A newspaper front page that sums up the world news of **Tuesday 24 November 2026** in a single image. Entry for the [make.fun competition `news-image-20261124`](https://make.fun/bounty/news-image-20261124).

## What the image shows

- **Main story:** the Nvidia rally fades on Tue 24 Nov — NVDA −6% after +31% on Mon, when Jensen Huang was reinstated as CEO on 23 Nov after direct pressure from President Trump (Reuters / Investopedia / CNA).
- **A schematic world map** with red dots marking where the stories happened, from the USA to Tokyo.
- **15 more lead stories** from every region: Huawei convicted on 10 of 12 counts, four tankers hit by mines in Hormuz, Ukraine's naval drones off Libya, Senegal's AFCON title restored by CAS, FIFA naming the 2031 and 2035 Women's World Cup hosts, the Hamas security chief killed in Gaza, the PIF tower hit in Riyadh, Houthis 60 km from Aden, the Colombia hostage crisis and car bomb, the Turkish helicopter crash, the Hanoi restaurant blast, Indonesia's VP succession, the Pentagon rebuking Canada, COP31 collapsing with no deal (22 Nov), and the ICJ's Myanmar genocide ruling (19 Nov).
- **A 24 Nov UTC timeline** and **32 wire briefs** from around the world.
- **A date-check footer:** every older story is dated in-line — ICJ ruling 19 Nov, COP31 collapse 22 Nov, Huang reinstatement and FIFA hosts 23 Nov — so nothing is presented as 24 Nov news unless it happened or was first reported on 24 Nov.

## Research

Revision 2 (25 Nov 2026), re-researched from scratch against Daily Summary Of (final edition 24 Nov 2026, 30 stories / 64 sources, each with a first-reported UTC time), Reuters (24 Nov), Just Security Early Edition 24 Nov 2026, FIFA, CAS/Reuters sport wires, and Investopedia + Reuters Trading Day (24 Nov close). Research pack: `../news-image-20261124-research-v2.md` in the workspace.

## How it was made

The front page is drawn from scratch by `main.py` (Python 3.13, standard library only): a hand-rolled 5×7 bitmap font, a scanline polygon filler for the map, and a hand-rolled PNG encoder. No network, no external assets — the program is fully deterministic and writes the same bytes on every run.

## How to run it

```sh
MAKEFUN_OUTPUT_DIR=out python3 main.py
```

This writes `out/entry.png` (1024×1024, PNG, under 1 MiB).
