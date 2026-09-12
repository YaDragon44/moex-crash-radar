# PROJECT CHECKPOINT — Настроение толпы / MOEX Crowd & Risk Intelligence

**Дата:** 2026-09-12  
**Репозиторий:** `YaDragon44/moex-crash-radar`  
**Текущая ветка:** `r1.5.1-oi-availability-pilot`  
**Активный PR:** #47 — `R1.5.1 — OI Data Availability & Incremental Value Pilot`  
**Production status:** **NO-GO**

---

## 1. Цель проекта

Создать Multi-Market Crowd & Risk Intelligence System, которая обнаруживает изменение поведения участников и рыночного режима раньше, чем это становится очевидно по цене.

Главная логика:

`DATA → QUALITY GATE → FEATURES → CROWD + MARKET + CONTEXT → RISK → TRANSITION → REGIME → ACTION`

Не предсказывать точную цену, вершину, дно или дату обвала. Основная задача — раннее выявление изменения риска и перевод этого изменения в действие с капиталом.

---

## 2. Главный исследовательский вывод к текущему checkpoint

Price-only ветка исследована глубоко и **остановлена**.

Последовательно не прошли устойчивую историческую проверку:

- универсальный EMA20/EMA50 Trend Core;
- breakout entry;
- breakout hold/retest;
- pullback/reclaim;
- price structure;
- early trend transition;
- structure + early trend R3 как универсальный regime rule;
- market-specific EQUITY SHORT R0/R2 после chronology robustness.

Итог R1.4.8.1:

`TECHNICAL_ONLY_STOP`

Причина: хорошие локальные результаты не подтвердили устойчивость по независимым временным периодам. Дальнейший перебор price-based индикаторов признан риском overfitting.

---

## 3. Последний полностью завершённый релиз

### R1.5.0 — OI + FIZ/YUR Positioning & Context Foundation

**Статус:**

`QUALITY FOUNDATION PASS | SOURCE CONTRACT PASS | ADAPTER/FEATURE TESTS PASS | PRODUCTION NO-GO`

Реализовано и протестировано:

- point-in-time Quality Gate;
- обязательная цепочка `event_time → available_time → decision_time`;
- защита от look-ahead;
- fail-closed семантика;
- `N/A`, `STALE`, `BLOCKED_AUTH` не считаются neutral;
- запрещён forward fill participant data;
- FUTOI Adapter interface;
- OI Feature Builder;
- OI features: total OI, ΔOI, ΔOI%, percentile, Price×OI quadrant, persistence;
- Source Availability Registry;
- regression/contract tests.

Последний CI run R1.5.0:

- Run: `34529435375`
- Result: **SUCCESS**
- Quality/source/adapter/feature tests: **PASS**
- Contract Gate: **PASS**

---

## 4. Критическое ограничение данных

### MOEX FUTOI

Исторический intraday FUTOI требует подписки/авторизованного доступа MOEX.

Семантика:

- `FIZ` — физлица;
- `YUR` — юрлица;
- `MOMENT` — market/event time;
- `SYSTIME` — publication/available time;
- частота продукта — intraday, 5 минут.

Без подтверждённого доступа:

`FUTOI = BLOCKED_AUTH`

Запрещено:

- подставлять нули;
- считать отсутствие данных neutral;
- заменять intraday FUTOI публичными daily-срезами;
- генерировать фиктивную историю FIZ/YUR.

---

## 5. Текущий релиз

### R1.5.1 — OI Data Availability & Incremental Value Pilot

**Ветка:** `r1.5.1-oi-availability-pilot`  
**PR:** #47  
**Статус:** `REQUIREMENTS FROZEN | AVAILABILITY GATE READY | IMPLEMENTATION NEXT | PRODUCTION NO-GO`

Цель — сначала доказать фактическую доступность point-in-time исторического OI, и только потом разрешить минимальный ablation.

Pilot universe:

- MX
- SI
- SR
- GZ

### Phase A — Availability Gate

Для каждого семейства нужно получить фактическую матрицу:

- source;
- field semantics;
- first timestamp;
- last timestamp;
- event_time semantics;
- available_time semantics;
- frequency;
- contract coverage;
- gaps;
- access mode;
- quality.

Правила:

- no forward fill;
- no inferred historical OI;
- no fabricated continuity;
- no FIZ/YUR daily substitution.

### DATA_READY Gate

`M1 Price + OI` разрешается только если валидная OI-history найдена минимум для:

- **2 pilot families**;
- **2 независимых chronological subperiods**;
- с корректной point-in-time семантикой.

Иначе:

`DATA_LIMITED → M1 backtest forbidden`

---

## 6. Следующий конкретный шаг

### R1.5.1 — OI Availability Collector

Необходимо реализовать и запустить collector, который по MX / SI / SR / GZ проверит реальные исторические источники OI и создаст артефакт покрытия.

Ожидаемый output:

`artifacts/r1_5_1_oi_availability_report.json`

Для каждого рынка:

- `status`;
- `source`;
- `first_timestamp`;
- `last_timestamp`;
- `records`;
- `frequency`;
- `contracts_found`;
- `gaps`;
- `event_time_semantics`;
- `available_time_semantics`;
- `quality`;
- `reason` при N/A/BLOCKED.

Итоговый Gate:

- `DATA_READY` → можно запускать M0 vs M1;
- `DATA_LIMITED` → backtest M1 запрещён;
- `BLOCKED_AUTH` → требуется доступ/подписка, ничего не симулировать.

---

## 7. План после Availability Gate

Если `DATA_READY`:

1. Заморозить price-only control M0.
2. Запустить M1 = M0 + OI без FIZ/YUR.
3. Сравнить M0/M1 по incremental value, а не по красивому Score.
4. Метрики: transition lead time, false alarm rate, precision/recall, signal stability, forward risk/return diagnostics.
5. Не оптимизировать +0.5% / P75 до evidence.

Если `DATA_LIMITED`:

1. Не строить synthetic OI history.
2. Зафиксировать Data Blocker.
3. Решить вопрос с историческим источником/подпиской.
4. Параллельно разрешено развивать только независимый Context Layer с валидной point-in-time историей.

---

## 8. Release history — ключевые статусы

| Release | Результат |
|---|---|
| R1.4.0 | Simple Entry Radar MVP |
| R1.4.1 | Public technical ablation; FULL gate rejected |
| R1.4.2 | Simplified Trend+Trigger |
| R1.4.3 | Minimum Tradable Version; later invalidated as production edge |
| R1.4.3.1 | Historical Stop Gate; ATR1.5 provisional |
| R1.4.3.2 | Robust stop validation; candidate only |
| R1.4.4 | Exit management experiment; PR closed unmerged |
| R1.4.5 | Complete backtest; **STRATEGY NO-GO** |
| R1.4.6 | LONG identified as primary defect |
| R1.4.6.1 | LONG breakout redesign NO-GO |
| R1.4.6.2 | LONG pullback/reclaim NO-GO |
| R1.4.6.3 | EMA trend core NO-GO |
| R1.4.7 | Regime redesign; R0/R1/R2 NO-GO, R3 sparse |
| R1.4.7.1 | R3 research candidate only |
| R1.4.7.2 | R3 extended history; non-robust |
| R1.4.8 | Market-specific segmentation; EQUITY SHORT candidates |
| R1.4.8.1 | Chronology robustness failed; **TECHNICAL_ONLY_STOP** |
| R1.5.0 | OI/FIZ/YUR/Context foundation; **QUALITY PASS** |
| **R1.5.1** | **CURRENT — OI Availability Pilot** |

---

## 9. Не делать

- не возвращаться к перебору EMA/RSI/MACD/price triggers для спасения стратегии;
- не объявлять Crowd/Risk Score вероятностью падения;
- не смешивать Context механически с Crowd Score;
- не считать FIZ/YUR = smart money;
- не генерировать данные при отсутствии источника;
- не давать strong production action при плохом Quality Gate;
- не запускать M1/M2/M3/M4 без достаточной historical coverage;
- не продвигать live radar как validated trading strategy.

---

## 10. Recovery instruction

Если чат прервался:

1. Открыть этот `PROJECT_CHECKPOINT_2026-09-12.md`.
2. Проверить ветку `r1.5.1-oi-availability-pilot` и PR #47.
3. Не повторять price-only исследования R1.4.x.
4. Продолжить с **OI Availability Collector**.
5. Сначала Phase A Data Availability Gate.
6. Только при `DATA_READY` переходить к M0 vs M1.
7. При любом конфликте между красивым результатом и Quality Gate приоритет всегда у Quality Gate.

---

## 11. Текущий GO / NO-GO

**Development:** GO  
**Data Quality Foundation:** GO  
**OI Historical Availability:** PENDING  
**FUTOI Historical Positioning:** BLOCKED_AUTH  
**Historical M1 Ablation:** LOCKED  
**Production Trading Strategy:** NO-GO  
**Live full-size / automated trading:** NO-GO

### NEXT ACTION

**Implement → Test → Run `R1.5.1 OI Availability Collector` → Produce coverage report → DATA_READY / DATA_LIMITED decision.**
