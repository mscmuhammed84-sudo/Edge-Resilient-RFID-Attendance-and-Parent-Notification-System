# LSASP lab: edge terminal, sync, cloud validator, security experiments

Standard library only (Python >= 3.10). **All data are synthetic. Nothing here is school data, and nothing
was measured on a Raspberry Pi 4 or on MFRC522 hardware.**

## Layout
- `lsasp/` protocol (v1 as described in the manuscript; v2 = HMAC-SHA256, T_event/T_tx, per-record validation,
  persistent nonce index, idempotent ack, per-terminal keys), clock, encoding.
- `edge/` SQLite schema/DB, event classification, terminal logic, RFID reader (mock + MFRC522 wrapper), sync with back-off.
- `cloud/` HTTP validation endpoint (put behind TLS), notification queue.
- `sim/` simulated link (outages, lost acks). `tests/` 27 unit tests. `experiments/` attacks, faults, scenarios, ablation, bench.
- `experiments/longrun.py` is the 50-day, 150-student simulation (synthetic workload, 5 seeds, 4 outage rates). `run_all.py` runs everything -> `results/` (results.md, results.json, attacks.csv).

## Run
    python -m unittest discover -s tests
    N_TRIALS=1000 python run_all.py        # ~5 min (the 50-day sweep dominates)

## Assumptions (v1 is reconstructed from the manuscript text, not from the authors' code)
- v1 token/hash are concatenations without delimiters; hash is unkeyed; freshness is two-sided (+-5 min) on the record timestamp.
- v1 stores a nonce only after the packet passes; nonce cache is in memory with TTL; whole batch is rejected on any failure.
- Time windows, debounce (30 s) and batch/back-off parameters are illustrative defaults.
- If the authors' real v1 differs, rerun against their implementation.

## Not tested / not provided
- `MFRC522Reader` on hardware; `SmtpMailer` against a real server; Firebase (no port); TLS (use a reverse proxy).
- Timing numbers are for this sandbox (Xeon 2.8 GHz, Python); they do not replace Raspberry Pi measurements.
- Clock integrity is not solved: v2 only bounds skew; an in-window wrong time is accepted by both versions.

## Release checklist (for the authors)
1. Push this folder to a public GitHub repository and create a release (tag v1.0.0).
2. Connect the repository to Zenodo and archive the release to obtain a DOI; put the DOI in `CITATION.cff` and in the paper's Data Availability Statement.
3. Check the license (MIT is a default chosen here; change it if your institution requires another).
4. Re-run `python -m unittest discover -s tests` and `N_TRIALS=1000 python run_all.py`, and compare `results/results.md` with the paper's tables (timings differ by machine).
