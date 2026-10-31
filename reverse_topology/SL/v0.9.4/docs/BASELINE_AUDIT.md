# Stage 0 — Baseline audit

Дата аудита: `2026-10-26T12:00:01-05:00` (вывод `date -Is`). Репозиторий: `/root/v0.9.4`.

## Проверенная архитектура

- `topology092/collect.py` — read-only acquisition, append-only ReadVar journal, bounded retries, reconnect/health checks, resume и snapshot-файлы.
- `topology092/readvar.py` — ограниченный S7 transport: SetupCommunication и ReadVar; WriteVar и drive-control отсутствуют.
- `topology092/sdb.py` — чтение/декодирование SDB.
- `topology092/topology.py` — TLV decode и принятие физического ребра только при reciprocal-проверке портов.
- `topology092/model.py` — сборка offline-модели и экспорт CSV/GraphML/JSON.
- `topology100/evidence.py` — нормализация сохранённых результатов; `topology100/cross_validate.py` существует, но Stage 0 его не переносит и не меняет.
- `tests/` содержит unit/regression проверки декодеров, recovery/resume и сохранённых CNC-результатов.

Сборщик и topology processing разделены: topology строится из сохранённых ReadVar/SDB; README документирует offline rebuild. Live CNC в этом аудите не использовался.

## Зависимости и запуск

`requirements.txt`: `python-snap7==2.0.2`, `pytest>=8.0`. Тестовая среда `.venv-test` фактически доступна. Архивные captures/runs сохранены; в каждом из `runs/cnc135` и `runs/cnc152` по 14 файлов, включая `capture.json`, ReadVar journal, SDB binaries и topology exports.

## Measured baseline

| Snapshot | CU | axes | physical edges (actual/target) | CU_LINK |
|---|---:|---:|---:|---:|
| `runs/cnc135` | 5 | 19/19 | 58/58 | 4 |
| `runs/cnc152` | 2 | 6/6 | 13/13 | 1 |

Оба `summary.json` имеют `capture_phase=COMPLETE`, `capture_complete=true`, полные TLV actual/target и равные actual/target edge sets.

## Cleanup sequence (после Stage 0)

1. Зафиксировать versioned domain contract, provenance/status/confidence и совместимость старых JSON/CSV.
2. Формализовать evidence chain axis → CU/DO → drive/module → motor/encoder и endpoint/port semantics.
3. Разделить config/state polling и определить read-only monitor API с bounded timeout/retry.
4. Ввести нормализованные события и историю с raw evidence references.
5. Выполнить независимую cross-validation по ARC/PDF/electrical только как отдельный анализ, не меняя runtime graph.
6. Затем добавлять UI/storage/operational CLI отдельными этапами.

Git недоступен (`git: command not found`), поэтому commit/branch baseline не заявляется.
