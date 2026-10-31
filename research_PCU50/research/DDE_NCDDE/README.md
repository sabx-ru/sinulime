# DDE / NCDDE — прямой низкоуровневый доступ

**Исследовательский и возможный запасной путь.** Начать с [FINDINGS_AND_OPEN_QUESTIONS.md](FINDINGS_AND_OPEN_QUESTIONS.md).

- `reverse/IMPORTANT_corrected_serializer_counter_and_OEM.md` — **последняя статическая коррекция**: реальный sender/sequence writer и путь до `DdeCreateDataHandle` в старом NCDDE. Старые документы, где writer объявлен полностью неизвестным, были уточнены. Данные не доказывают идентичность каждого runtime ответа статическому буферу.
- `reverse/annotated_ncdde_old_serializer.md`, `reverse/phase12_serializer_trace.md`, `reverse/phase9_serializer_reconstruction.md` — сохранённый путь производителя и структура сериализатора. Старые phase9 выводы о writer/counter **частично устарели**, приоритет у corrected-bytes документа.
- `reverse/raw_disassembly_and_xrefs.tar.gz` + `reverse/RAW_TRACE_MANIFEST.json` — полный отобранный первичный дизассемблерный вывод, без повторов идентичных файлов.
- `experiments/pcu_baseline/raw/` — 198 бинарных + 69 текстовых ответов первого прогона, их оригинальные DDE instrument logs; `pcu_phase14/raw/` — 579 бинарных + 396 текстовых ответов второго прогона.
- `experiments/*/console/` — оригинальные вызовы DDE, результаты, последовательность и время. Глобальные session summaries и промежуточные MCVar-чтения находятся в `../MCVar/experiments/.../console/`.
- `tools/capture_reader.py` — предпочтительный строгий парсер/валидатор, не пытается отличить 8-байтную строку от BCD только по `(100,6)` и длине. `tools/phase12/` — оригинальный несовершенный парсер (сохраняется как тестируемая история).
- `tools/windows_dde_probe.cpp`, `tools/bin` — оригинальный исходник и EXE ограниченной read-only DDE diagnostics; EXE может требовать отсутствующей GCC DLL.

**Не установлено:** полный внешний encoder протокола, однозначные типы без адресного контекста, причинная цепь MCVar→DDE, количество запросов на сети PCU→NCU. Значение счётчика `+7` наблюдалось в реальных ответах, но корреляции не равны доказанным сетевым запросам.
