# Лог разработки v1.0.0

## Проект

SINUMERIK 840D sl / SINAMICS read-only topology reconstruction.

Корень проекта:

```text
/root/v0.9.4
```

## Исходная версия

Рабочее ядро: `v0.9.4`.

Основные источники:

- `topology092/` — сбор, декодирование SDB, ReadVar и реконструкция топологии;
- `runs/cnc135/` — offline-снимок станка 135;
- `runs/cnc152/` — offline-снимок станка 152;
- `ARCs/` — ARC-архивы станков 135 и 152;
- `electrical/` — электрические схемы станков 135 и 152;
- `analysis_stage1/` — материалы reverse engineering Create MyConfig;
- `req.txt` — требования проекта.

## Предварительный reverse engineering

Исследован установочный комплект Create MyConfig и извлечён `Data1.cab`.

Основные обнаруженные компоненты:

- `topo.exe`;
- `uptdata.dll`;
- `upconvert.dll`;
- `upverify.dll`;
- `updatabase.dll`;
- `arc.dll`;
- `archive.dll`;
- `netclient.dll`;
- базы описаний `*.info` и `*.para`;
- шаблоны XML;
- документация Topo/Create MyConfig.

Восстановлена объектная иерархия Create MyConfig:

```text
UPTProject
  → Topo
      → Bus
          → Slave
              → SiComponent
                  → Cliq port
                      → вложенный компонент
```

Ключевые выводы:

- Create MyConfig использует иерархическую модель UPTData;
- `Cliq` является объектом порта компонента, а не только графическим ребром;
- `Cliq.Index` соответствует индексу порта;
- `Cliq.Uplink` и `CuLink` связаны с меж-CU-представлениями;
- `v0.9.4` реализует независимую evidence-модель и не копирует внутренний формат Siemens;
- декомпилированный Siemens-код и DLL не включаются в реализацию проекта.

Документация reverse engineering:

```text
/root/analysis_stage1/reverse_engineering_summary.md
```

## Проверка v0.9.4

В окружение `.venv-test` установлены:

```text
python-snap7==2.0.2
pytest==9.1.1
```

До начала v1.0.0 выполнено:

```text
35 passed, 4 subtests passed
```

Подтверждена read-only архитектура:

- S7 ReadVar;
- SDB Upload;
- отсутствие S7 WriteVar;
- отсутствие S7 Download;
- отсутствие NC MD write;
- отсутствие команд создания ARC на контроллере.

## Требования проекта

Требования сохранены в `/root/req.txt`.

Основные цели:

1. read-only сбор NCK/SDB/SINAMICS;
2. восстановление цепочки оси и оборудования;
3. однозначная связь логических и физических объектов;
4. NiceGUI web-интерфейс;
5. циклический мониторинг, события и история;
6. адаптация по данным ЧПУ без обязательной зависимости от схем и ARC.

Вывод: `v0.9.4` является рабочим read-only ядром реконструкции, но ещё не полной системой мониторинга.

## Начало v1.0.0

## Reviewer cross-validation fixes

- `_compare_edges` now preserves duplicate endpoint inventory and compares counters.
- Actual/target deltas are endpoint-level and report component, port, and edge deltas separately.
- Reciprocal-port validation resolves the actual reverse port and selector format; missing values remain machine-readable and bounds are type/non-negative checks.
- CU_LINK expected-pair counts participate in assertions.
- ARC remains inventory-only and electrical sources remain corroboration-only.
- Regression/full verification: `47 passed, 4 subtests passed`.

Создан пакет:

```text
/root/v0.9.4/topology100
```

Файлы:

- `topology100/evidence.py`;
- `topology100/__init__.py`;
- `topology100/__main__.py`;
- `tests/test_topology100.py`.

Версия и схема:

```text
VERSION = 1.0.0
SCHEMA = read-only-topology/v1.0.0
```

Добавлена evidence-модель с разделением:

- `axes`;
- `drives`;
- `components`;
- физические `connections`;
- typed relations;
- `unresolved_ports`;
- `mapping_problems`;
- provenance;
- SHA-256 исходного ReadVar-журнала.

Для объектов и связей сохраняются:

- `status`;
- `confidence`;
- источник данных;
- параметры и индексы ReadVar;
- идентификаторы CU/bus/slave/DO/component.

## Добавленная цепочка оборудования

Реализована консервативная цепочка только по подтверждённым ReadVar-ссылкам:

```text
Axis
  → Servo/DO
  → Motor Module
  → Motor
  → Sensor Module
  → Encoder
```

Добавленные виды отношений:

- `AXIS_TO_DRIVE`;
- `DRIVE_TO_MOTOR_MODULE`;
- `DRIVE_TO_MOTOR`;
- `DRIVE_TO_SENSOR_MODULE`;
- `SENSOR_TO_ENCODER`.

Неподтверждённые связи не дорисовываются и получают статус `unresolved`.

## Offline-прогоны v1.0.0

Команда обработки:

```bash
.venv-test/bin/python -m topology100 \
  --reads runs/cnc135/readvar/reads.jsonl \
  --sdb runs/cnc135/sdb \
  --out runs/v1.0.0/cnc135
```

Аналогично выполнен прогон для `cnc152`.

Результаты:

```text
/root/v0.9.4/runs/v1.0.0/cnc135
/root/v0.9.4/runs/v1.0.0/cnc152
```

### cnc135

- 5 CU;
- 19 подтверждённых осей;
- 95 компонентов;
- 19 servo/DO;
- 58 физических DRIVE-CLiQ-рёбер;
- 113 equipment relations;
- 235 нормализованных connection records.

Типы связей:

```text
DRIVE_CLIQ_CABLE       58
ANALOG                 32
MECHANICAL             32
AXIS_TO_DRIVE          19
DRIVE_TO_MOTOR_MODULE  19
DRIVE_TO_MOTOR         19
DRIVE_TO_SENSOR_MODULE 28
SENSOR_TO_ENCODER      28
```

### cnc152

- 2 CU;
- 6 подтверждённых осей;
- 23 компонента;
- 6 servo/DO;
- 13 физических DRIVE-CLiQ-рёбер;
- 30 equipment relations;
- 59 нормализованных connection records.

Типы связей:

```text
DRIVE_CLIQ_CABLE       13
ANALOG                  8
MECHANICAL              8
AXIS_TO_DRIVE           6
DRIVE_TO_MOTOR_MODULE   6
DRIVE_TO_MOTOR          6
DRIVE_TO_SENSOR_MODULE  6
SENSOR_TO_ENCODER       6
```

## Проверка после модификаций

Итоговый запуск:

```text
38 passed, 4 subtests passed in 4.05s
```

Базовые результаты `v0.9.4` сохранились:

- `cnc135`: 19/19 осей, 58 физических рёбер;
- `cnc152`: 6/6 осей, 13 физических рёбер.

## Cross-validation этап

Выполнен первый независимый cross-validation без изменения runtime-графа.
Добавлены:

- `topology100/cross_validate.py` — воспроизводимый анализ ARC DP и PDF;
- `tests/test_cross_validate.py` — 3 regression-проверки;
- `runs/v1.0.0/CROSS_VALIDATION.md` и `.json` — отчёт;
- `topology100/README.md` — документация процедуры.

Результаты:

- ARC DP для `cnc135`: 43 уникальных ACX-пути; для `cnc152`: 13;
- множества `(bus_id, slave)` ARC совпадают с ReadVar/SDB для обоих снимков;
- сохранённые сводные значения v0.9.4 полностью совпадают с v1.0.0;
- PDF независимо содержит термины Drive-CLiQ, motor module и encoder;
- ARC DP не предоставляет декодированных component number/device_id/port selector;
- текст PDF не даёт стабильного машинного endpoint mapping для каждой связи.

Следствие: ARC/PDF подтверждают инвентарь и общий тип оборудования, но не
подтверждают индивидуальные рёбра. Ни одна связь не добавлена в runtime-граф
на основании ARC или electrical.

Проверка после cross-validation:

```text
43 tests passed, 4 subtests passed
```


1. Cross-validation по ARC и электрическим схемам.
2. Проверка новых axis/drive/equipment chains на независимых источниках.
3. Уточнение семантики motor и encoder references.
4. Выделение конфигурационных и динамических ReadVar-параметров.
5. Read-only monitor service.
6. Нормализованные события и SQLite/JSONL history.
7. NiceGUI-интерфейс поверх model/state API.

ARC и электрические схемы не должны использоваться для дорисовки runtime-графа. Они применяются только для независимой проверки и классификации расхождений.
