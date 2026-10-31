# Stage 0 — Known issues

Статусы ниже разделяют воспроизведённое/подтверждённое состояние v0.9.4 и будущую design work. Исправления production code в Stage 0 не выполняются.

## KI-001 — Нет стабильного versioned domain contract

- **Статус:** подтверждено как design work; roadmap Stage A.
- **Пути:** `topology092/model.py`, `topology092/collect.py`, `ROADMAP_REQUIREMENTS.md` (Этап A).
- **Влияние:** внутренние JSON/CSV ещё не являются единым контрактом с обязательными source/status/confidence/timestamp/raw reference.
- **Correction/regression:** ввести versioned models без изменения старых форматов; regression — offline rebuild `cnc135`/`cnc152` и существующий test suite.

## KI-002 — Evidence chain ось → физическое оборудование неполная

- **Статус:** подтверждено; roadmap называет CU/DO/component chain и motor/encoder chain частично выполненными.
- **Пути:** `topology092/model.py`, `topology092/topology.py`, `ROADMAP_REQUIREMENTS.md` (Этап B).
- **Влияние:** не каждая логическая связь до motor/encoder имеет единый доказательный объект.
- **Correction/regression:** формализовать evidence references и unresolved status; сохранить 19/19 и 6/6 осей без inference.

## KI-003 — Порты/selectors и неоднозначные mappings требуют общей модели

- **Статус:** подтверждено; текущий код отклоняет missing/ambiguous reciprocal mappings, но пользовательской endpoint-модели нет.
- **Пути:** `topology092/topology.py`, `topology100/evidence.py`, `tests/test_topology092.py`, `tests/test_cross_validate.py`.
- **Влияние:** ambiguous, missing и selector mismatch должны быть видимыми, а не превращаться в физическое ребро.
- **Correction/regression:** endpoint objects с selector/ordinal/reason; regression на missing, reciprocal mismatch, incomplete TLV и duplicate edges.

## KI-004 — Одноразовый capture, а не циклический monitor service

- **Статус:** подтверждено; roadmap Stage D.
- **Пути:** `topology092/collect.py`, `topology092/__main__.py`, `ROADMAP_REQUIREMENTS.md` (Этап D).
- **Влияние:** нет scheduler/state polling и явного разделения редкой конфигурации и динамического состояния.
- **Correction/regression:** добавить read-only MonitorSession поверх acquisition; regression на timeout, reconnect, changed identity и отсутствие write calls.

## KI-005 — Нет нормализованной event/history модели

- **Статус:** подтверждено; есть JSONL read journal, но roadmap отмечает отсутствие event model/severity/history.
- **Пути:** `topology092/collect.py`, `ROADMAP_REQUIREMENTS.md` (Этапы E/G).
- **Влияние:** item errors, connection failures и topology/state changes не представлены единым queryable event contract.
- **Correction/regression:** добавить UTC timestamp, snapshot/station identity, source address, old/new value и raw reference; проверить восстановление события из raw journal.

## KI-006 — UI и storage/service interfaces отсутствуют

- **Статус:** подтверждено; roadmap отмечает отсутствие NiceGUI и storage/monitor interfaces.
- **Пути:** отсутствие UI-пакета в дереве; `ROADMAP_REQUIREMENTS.md` (Этапы F/G).
- **Влияние:** текущий результат доступен через файлы/CLI, без отдельного view/state слоя.
- **Correction/regression:** добавлять UI только поверх model/state API; не допускать прямого чтения станка из UI.

## KI-007 — ARC/PDF/electrical cross-validation не является Stage 0 core

- **Статус:** подтверждено как граница этапа; `topology100/cross_validate.py` не переносится и не изменяется.
- **Пути:** `topology100/cross_validate.py`, `topology100/README.md`, `runs/v1.0.0/CROSS_VALIDATION.*`.
- **Влияние:** Stage 0 не утверждает ARC/PDF endpoint mapping и не добавляет runtime edges из внешних источников.
- **Correction/regression:** отдельный future analysis сохраняет `confirmed/unresolved`, не изменяет captures/runtime graph; production core не получает PDF/electrical/ARC parser.

## KI-008 — Live CNC и git baseline недоступны в этой проверке

- **Статус:** подтверждено ограничение среды, не production bug.
- **Пути:** `/root/v0.9.4`; `git` отсутствует; live commands не запускались.
- **Влияние:** baseline подтверждён offline fixtures и replay, но сетевое поведение на live CNC не сертифицировано; commit/branch сравнение невозможно.
- **Correction/regression:** отдельная safety-reviewed стендовая проверка read-only transport; повторить тесты без live write operations и зафиксировать commit только в среде с git.
