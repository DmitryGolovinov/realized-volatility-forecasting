PY ?= python
.PHONY: test demo data-public reproduce-public data-private dates-private reproduce-private \
	data smoke-real reproduce report check
RUNS := dev final crypto_dev crypto_final crypto_g21_dev crypto_g21_final

test:              ## offline tests on synthetic fixtures (tests needing private inputs skip)
	$(PY) -m pytest -q
demo:              ## synthetic HAR process, no network, writes results/demo/
	$(PY) scripts/demo.py
data-public:       ## PUBLIC inputs only: Binance spot 5-minute klines (~0.3 GB, SHA-256 checked)
	$(PY) scripts/build_crypto_panel.py
reproduce-public:  ## crypto transfer (development rows) on both panels + paired losses + reports
	$(PY) scripts/run_crypto.py --mode dev --panel crypto
	$(PY) scripts/run_crypto.py --mode dev --panel crypto_g21
	$(PY) scripts/paired_losses.py crypto_dev crypto_g21_dev
	$(PY) scripts/make_report.py crypto_dev
	$(PY) scripts/make_report.py crypto_g21_dev
data-private:      ## PRIVATE supplied stock files (not redistributed; see docs/data.md)
	@test -f data/raw/AAPL_data.parquet || (echo "The archival stock study needs the five \
	supplied *_data.parquet files and macro_data.parquet in data/raw/. They are not \
	redistributed. The public crypto study does not need them: make data-public." && exit 1)
dates-private: data-private  ## optional inferred calendar for the stock rows (extra: dates)
	$(PY) scripts/recover_dates.py
reproduce-private: data-private  ## archival stock study, development rows
	$(PY) scripts/run_study.py --mode dev
	$(PY) scripts/paired_losses.py dev
	$(PY) scripts/make_report.py dev
data: data-public
smoke-real: reproduce-public
reproduce: reproduce-public
report:            ## rebuild tables and figures from whichever run artifacts exist
	@for r in $(RUNS); do if [ -f results/$$r/manifest.json ]; then \
	$(PY) scripts/make_report.py $$r || exit 1; fi; done
check: test
	$(PY) -m ruff check src tests scripts
	$(PY) scripts/check_claims.py
