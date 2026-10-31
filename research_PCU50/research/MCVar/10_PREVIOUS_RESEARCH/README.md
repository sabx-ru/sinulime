# MCVar — COM интерфейс Siemens

**Приоритетный путь создания PowerLine-коллектора.** Начать с [FINDINGS_AND_OPEN_QUESTIONS.md](FINDINGS_AND_OPEN_QUESTIONS.md), а не со старых phase-отчётов.

- `api/COM_API_REFERENCE.{md,json}`, `api/resources/{old,new}_TYPELIB_1_1033.bin`, `api/variable_catalog.*` — обнаруженный COM интерфейс и исходные ресурсы (async/cyclic только по статическим именам).
- `reverse/IMPORTANT_corrected_COM_lifetime_and_vtable.md` — **последняя важная коррекция**: действительный старый body `ReadVar` начинается около `0x1000BC30`; `0x1000BC74` — метка внутри тела. `0x10014CBE` — COM lifetime/cleanup, а не доказанный отправитель DDE-запроса. Косвенный call `0x10004E2E` остаётся непрослеженным. Более старые `reverse/*.md` могут содержать устаревшие подписи.
- `reverse/raw_disassembly_and_xrefs.tar.gz` + `reverse/RAW_TRACE_MANIFEST.json` — оригинальные машинные листинги MCVar и связанные статические проверки; раскрывать перед очередным reverse.
- `experiments/pcu_baseline/runner/` — **оригинальные** `RUN_ALL.cmd`, три Windows x86 исполняемых средства (MCVar/DDE/watchdog) и 24 исходные конфигурации. Исходники исполняемых файлов из этого архива не восстановлены: собранные EXE сохранены неизменными.
- `experiments/pcu_baseline/console`, `experiments/pcu_baseline/raw` — реальные ответы, качества, ошибки из первого прогона; `pcu_phase14/` — из второго.
- `sdk/phase13_original/` — исторический прототип с **известными ошибками**, не рабочий Siemens COM адаптер: last-good, freshness, timestamp, отсутствие STA-owner. Не использовать в production без исправления.
- `tools/windows_typeinfo_probe.cpp` — исходник COM TypeInfo; `tools/bin` — старый EXE, у которого может отсутствовать GCC DLL-зависимость.
- `analysis/` — сохранённые результаты offline batching и event ledger; `phase9_older_event_ledger.json` ссылается на ранние захваты, не все из которых доступны в этом наборе.

**Не установлено:** действующий ReadVarCyclic callback, количество NCU TCP транзакций на массив из N значений, точный IPC path MCVar→NCDDE. Для доказательства transport требуется реальная трасса коррелированных запросов, а не ещё один дизассемблинг тех же адресов.
