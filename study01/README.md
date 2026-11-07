# Singapore Business Signals — Study 01: Early-Warning Indicators for F&B Demand

**Author:** Alfred Ling, independent researcher, Singapore
**DOI:** [10.5281/zenodo.24039615](https://doi.org/10.5281/zenodo.24039615)
**Report:** [`report/Study01_Report.pdf`](report/Study01_Report.pdf) ([Markdown version](report/Study01_Report.md))

## Question

Do public business expectations (SingStat Business Expectations of the Services Sector) and international visitor arrivals (STB) improve forecasts of Singapore's F&B sales **volume** over the next three months, compared with sales history alone?

The target is the average year-on-year growth of the Food & Beverage Services Index (chained volume, 2025=100, i.e. adjusted for price changes) over the following three months. Note that SingStat's headline monthly F&B figures are usually quoted at current prices (sales value), so they will differ from the volume figures used here.

## Result

24 monthly forecast origins, July 2024 to June 2026. Mean absolute error (MAE) in percentage points:

| Model | MAE | RMSE |
|---|---|---|
| A: sales history | 1.689 | 2.393 |
| B: + revenue expectations | 1.872 | 2.257 |
| C: + expectations and visitor arrivals | 1.789 | 2.187 |
| Zero-growth benchmark | 1.432 | 1.882 |

Zero growth beat all three pre-specified models on MAE and RMSE in this test. Contrary evidence is kept in the report: B and C reduced RMSE relative to A, and a pre-specified variant without month-of-year controls let model C narrowly beat zero growth on MAE (1.426) while doing worse on RMSE.

## Limitations (read before citing)

- Retrospective pseudo-out-of-sample test on revised data snapshots with assumed publication delays. It does not reconstruct what forecasters actually saw in real time.
- Only 24 overlapping test windows, 20 of them at or below zero growth.
- Tuning was dominated by pandemic-era errors, and every model selected the strongest penalty in the search grid.
- The preregistration is an internal timestamped protocol, not an external registry entry.
- Results apply to these models and this period, not to sentiment or tourism data in general.

AI tools assisted with source collection, coding, analysis, drafting and methodological review, under the author's direction and review. The reviews are AI-generated and internal, not academic peer review. Public data only; views are the author's own and do not represent any employer.

## Contents

| Path | What it is |
|---|---|
| `report/` | Report (PDF and Markdown) |
| `raw/` | Original public API responses (JSON) and retrieval metadata |
| `code/` | Analysis pipeline (`analyse.py`), independent verification (`verify.py`), charts and workbook inputs (`deliver.py`), and the original download script (`download.py`, for audit only) |
| `output/` | Aligned data, all predictions, metrics, robustness checks, uncertainty intervals, charts, evidence workbook and the locked protocol (`preregistration_v1.txt`) |
| `audit/` | Execution notes, original model and protocol locks, and the original package hash manifest |
| `Study01_Colab.ipynb` | Rerun everything in Google Colab without a local Python setup |
| `SHA256SUMS.json` | Hashes for every file in this release |

## Reproduce

Python 3.11+. From this folder:

```bash
python -m pip install -r requirements.txt
python code/analyse.py --stage prepare
python code/analyse.py --stage validate
python code/analyse.py --stage final
python code/verify.py
python code/deliver.py
```

Expected primary MAE: A 1.6890898915, B 1.8724573516, C 1.7893909438 (tiny floating-point differences are possible). Rerunning `validate` writes new timestamps to `output/model_lock.json`; the original locks are kept in `audit/`.

Do **not** run `code/download.py` to reproduce the study: live downloads give a different data vintage, including data after the 6 November 2026 cutoff.

**Colab:** open `Study01_Colab.ipynb` in Google Colab, upload `Study01_Reproducibility.zip` from the Zenodo record, and run all cells. The notebook checks the file hashes before running.

## Release notes

This public release (v1.0, 8 November 2026) is the frozen analysis package with these changes only: a new README, licences, a citation file and the revised report added; superseded drafts (an earlier paper version, a social media draft and the script that generated the earlier paper) removed; and one private protocol link replaced with the path to the included protocol file (in the workbook's Protocol tab, `output/workbook_inputs.json` and the matching string in `code/deliver.py`). Data, analysis logic and numerical outputs are unchanged. The original manifest is kept at `audit/original_SHA256SUMS.json`; `SHA256SUMS.json` covers this release.

## Licence

Report, data outputs and documentation: [CC BY 4.0](LICENSE-CC-BY-4.0.md). Code (`code/`, `Study01_Colab.ipynb`): [MIT](LICENSE). Raw source data remain subject to the terms of their publishers (SingStat, data.gov.sg Open Data Licence, STB, ACRA).

## Citation

Ling, A. (2026). *Singapore Business Signals — Study 01: Early-Warning Indicators for F&B Demand* (Version 1.0). Zenodo. https://doi.org/10.5281/zenodo.24039615
