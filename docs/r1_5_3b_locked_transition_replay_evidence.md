# R1.5.3-B — Locked Public Market-Transition Replay Evidence

**Status:** PASS — research evidence only / PRODUCTION NO-GO  
**Date:** 21.09.2026  
**Implementation:** PR #88, merge commit 41a5db6b  
**Evidence run:** GitHub Actions 35610962573, conclusion SUCCESS  
**Artifact:** historical-evidence / r1_5_3b_transition_replay.json, SHA-256 f326e6862da5f2f09b1347692eb85f3c523601f3f5efa99c3c73d35550eb2f3f

## Locked protocol

The run used the preregistered 2019-03-22–2026-09-18 public MOEX period, 2024-01-01–2026-09-18 untouched holdout, next-20-session drawdown outcome <= -8%, 70% coverage gate and fixed M0–M4 definitions. No threshold, split, horizon or source formula was changed after results.

Data: 1,883 index rows; 1,823 point-in-time evidence rows; 77 requested and 77 usable historical constituents; no failed securities.

## Holdout result

| Model | Alerts | True positives | Precision | Recall | False-alarm rate |
|---|---:|---:|---:|---:|---:|
| M0 — Price | 355 | 67 | 18.87% | 44.37% | 81.13% |
| M1 — Price + Breadth | 43 | 11 | 25.58% | 7.28% | 74.42% |
| M2 — Price + Breadth + Volume | 36 | 10 | 27.78% | 6.62% | 72.22% |
| M3 — Price + Breadth + Volatility | 2 | 0 | 0.00% | 0.00% | 100.00% |
| M4 — Price + Breadth + (Volume or Volatility) | 37 | 10 | 27.03% | 6.62% | 72.97% |

M4 versus M0: precision +8.16 percentage points; recall -37.75 percentage points.

## Gate decision

**PASS** under the preregistered executable criterion: M4 holdout precision exceeds M0 and M4 recall is non-zero.

This is not a production GO. M4 is much more selective but loses substantial recall; its false-alarm rate also remains high. The evidence does not justify changing Crash Score, Crash State, EXIT Gate, source actions, RADAR actions or Market UI.

## Reproducibility and failure boundary

The run is automated by the existing historical-evidence workflow and publishes its JSON artifact. Unit tests verify the frozen M4 condition, 70% fail-closed coverage and 20-session outcome. Missing evidence remains excluded; no backfill, retuning or future constituent leakage is permitted.

## Next state

R1.5.3-B is closed as research **PASS / production NO-GO**. Any future variant requires a separate preregistered hypothesis; it must not overwrite this result or be presented as a production signal.
