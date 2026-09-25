# Data card

- **Files (PRIVATE: supplied with the original exercise; local import to `data/raw/`, not
  redistributed; `make data-private` checks for them):**
  `AAPL/JPM/IBM/BA/PG_data.parquet` (4,257 rows each) and `macro_data.parquet` (4,257 rows).
  SHA-256 digests are recorded in every run manifest.
- **No dates in the files; calendar inferred (not authoritative).** Every file has a RangeIndex 0..4256. Rows are
  aligned across assets (cross-asset log-RV correlation peaks at lag 0) and with the macro file.
  The refit clock stays the frozen 252-row unit. The calendar is recovered in
  `data/date_map.csv` (`scripts/recover_dates.py`, method in `src/rvf/dates.py`): `r_d` equals
  min(open-to-close return, 0), so its sign identifies each row's trading day. Aligned to public
  daily Open/Close (Yahoo Finance via yfinance, downloaded at run time, not stored), the five
  stocks' signs agree on 95.4-98.1% of asset-days, against 49% when the calendar is shifted by
  one day. A monotone Viterbi alignment that allows the panel to omit exchange days dates every
  row: row 0 = 2001-01-29, row 4256 = 2018-01-02, and two exchange days are absent from the panel
  (2005-08-03, 2013-06-06). Development rows 1000..3404 = 2005-01-24..2014-08-14; reserved
  final rows 3405..4256 = 2014-08-15..2018-01-02. The position of each omission is then checked
  on the SIZE of r_d against min(open-to-close, 0) within +/-3 rows: the 2013 omission is clear
  (absolute distance 0.012 versus 0.027 for the next position), the 2005 one weaker (0.015 versus
  0.019), so one row next to 2005-08-03 could be one day off; no calendar-year boundary is
  affected. The recovery reads the sign and size of r_d in all rows, including reserved rows
  (metadata only: no variance, target, or model output). Provenance, margins and agreement
  statistics: `data/date_map_provenance.json`. Four rows agree for at most two of the five
  stocks. The reference prices come from a secondary source (Yahoo Finance), and the result is
  an inference, not a validation against an authoritative date file. It also does not reproduce
  the sample described by Christensen, Siggaard & Veliyev, "29 January 2001 to 31 December
  2017, or 4,235" trading days: the supplied panel has 4,257 rows and, under this alignment, ends
  on 2018-01-02, so the panel is not that paper's exact sample and its construction is not
  documented. Forecasts, refits and the development/final split use the row index only; the
  dates affect labels and calendar-year tables.
- **Verified identities:** rv_w and rv_m are trailing means of rv_d over rows t-4..t and
  t-21..t; rv_n + rv_p = rv_d (negative/positive semivariances). All features at row t are
  therefore known at the end of day t; the target is rv_d at row t+1 (daily realized variance).
- **Semantics inferred against public data:** r_d = min(open-to-close return, 0); r_w and r_m
  are non-positive weekly/monthly analogues; for JPM, `mom1w` tracks the 5-day return (correlation 0.84)
  and `dolvol` the daily log change of dollar volume (0.96). Still unclear: rq_d is negative in ~70% of rows, so it is not a raw quarticity; the macro columns
  (vix, epu, us3m, hsi, ads) are not in their usual units (e.g. `vix` ranges 3.3..719 and is
  weakly correlated with iv). Macro series have unknown release timing and vintage and are used
  only in a labeled retrospective sensitivity (HARX_macro, RF_macro).
- **Samples:** development rows 0..3404 (walk-forward forecasts from row 1000; headline rows
  1252..3403, where the combinations also exist). Reserved final: rows 3405..4256 of every
  asset. AAPL's final block was evaluated in the original exercise and is labeled previously
  viewed; the other assets' final blocks were not evaluated but cover the same period.

## Generation 2 transfer panel: crypto realized variance (public, dated)

- Source: Binance public spot 5-minute klines (monthly archives, data.binance.vision), each
  verified against the published SHA-256 (744 archives, 290 MB, cached in `data/crypto_raw/`,
  not redistributed). Assets fixed before download: BTC, ETH, BNB, XRP, ADA, LTC, TRX, XLM
  (all quoted in USDT). Days 2019-01-01..2026-08-31 (2,800 UTC days each; 2018-12 only warms up
  the 30-day features). Build: `scripts/build_crypto_panel.py`; definitions in
  `configs/g2_crypto_transfer.yaml` and `src/rvf/crypto.py`.
- Daily features from 288 five-minute log returns per UTC day (close to close; the price change
  across a missing bar is booked on the next bar): rv_d, semivariances rv_n/rv_p, quarticity,
  7/30-day trailing means (the 24/7 analogue of 5/22 trading days), r_d/r_w/r_m negative parts
  of open-to-close returns, 7-day momentum, log change of quote volume. No implied volatility,
  earnings dates or macro series exist for these assets, so those features are absent.
- Quality: 21 days per asset have at least one missing bar; 17 of them (exchange-wide
  maintenance or outages, all before 2024) have fewer than 95% of their bars, the worst 168 of
  288 (2019-05-15). One of them (2023-03-24, 272 bars) is a development target day; no final day
  is affected. No UTC day is missing and no realized variance is zero. Two panels are built from
  the same archives: `data/crypto/` (Generation 2: quarticity with complete-grid scaling) and
  `data/crypto_g21/` (Generation 2.1: span-aware quarticity; also stores `span_k2`); every other
  column is identical (methodology, "Missing bars and quarticity").
- Public route: `make data-public` needs no supplied stock file and no calendar recovery; the
  archives are public but are not redistributed here (checksums in `data/crypto*/manifest.json`).
- Samples: development rows up to 2023-12-31 (walk-forward forecasts from 2021-09-27, headline
  rows from 2022-06-06 where the combinations exist); reserved final 2024-01-01..2026-08-31.
