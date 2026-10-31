# Происхождение, сохранность и воспроизведение

## Из чего собран архив

- Основной источник: загруженный `stages.tar` (Stage 15, 16, 16.5, 16.6, 16.7, 16.7 Final).
- Два **оригинальных ресурса TypeLib** скопированы из ранее собранного `PowerLine_research_MCVar_DDE_NCDDE.zip` без модификации и проверены по известным SHA-256.
- Три небольших индекса/отчёта Phase 14 включены из ранее сохранённого каталога `research`; исходные PCU логи не дублировались.
- Полные оригинальные Siemens MCVar.dll не включены: они должны оставаться в `PCU_old` и `PCU_new` на машине исследователя. Никаких DLL не синтезировано.

## Контроль содержимого

- `FILE_MAP.csv`: каждая сохранённая запись `исходный путь -> новый путь`, размер, SHA-256.
- `CURATION_REPORT.json`: удалённые файлы и причины; большая часть исходных 2 150 файлов была внутри `.venv`/Python cache, прочие дубли удалены по SHA-256.
- `verify_consolidated.py`: проверяет все SHA, JSON, ABI vs TypeLib decoded, наличие ожидаемых evidence и TypeLib SHA. Эти проверки **не равнозначны Windows/PCU runtime**.
- `RESTORE` вспомогательные функции не перезаписывают оригиналы и пригодны для восстановления старого `/root/PL/stages` в отдельном каталоге.

## Исходные версии бинарников

- old `MCVar.dll` SHA-256 `43a5c1991d98b6b6e155233a0114d7ff72bf4dec7edf58d0607da501e7d98712`.
- new `MCVar.dll` SHA-256 `5e7d955ebe7cfd52424b04e91471b7408f42bf6cc427e3d94c50bc7f4428c24a`.
- old TypeLib resource SHA-256 `0653a34a342fc6b80e9f675ff9754173b878a353744098e6eb0c9fa429c77bb3`.
- new TypeLib resource SHA-256 `a7d9968596b9e9a17dff6fc2fcf4a2e2ddc65cedd28dba76eb77791b49dadfd1`.

## Воспроизводимость оригинальных проверок

Расположение выбранных скриптов изменено для удобства поиска по тематике. Большинство оригинальных скриптов жёстко используют `/root/PL/stages/...` и `/root/PL/PCU_old`/`PCU_new`. Чтобы воспроизвести их без ручной правки:

```bash
# только показывает, что будет восстановлено
python3 research/MCVar/00_OVERVIEW/restore_original_paths.py --dest /tmp/pl_stage_replay --dry-run

# копирует сохранённые фрагменты в /tmp/pl_stage_replay/stages/
python3 research/MCVar/00_OVERVIEW/restore_original_paths.py --dest /tmp/pl_stage_replay
```

Затем исследователь может настроить скрипты под эту копию либо перенести с явным контролем нужные файлы в исходную `/root/PL/stages` структуру; не перезаписывать действующие stage files автоматически. Для повторной **полной** проверки vtable нужны оригинальные Siemens DLL с правильными хешами и Python `pefile`; в этом архиве только записанный результат агентов и `.rdata` дампы.

## Ghidra проекты

Сохранён `07_PRIMARY_EVIDENCE/stage16_7/ghidra_project/` со служебными `*.gpr` и `*.rep` от двух версий. Эти артефакты могут ускорить будущую работу, но их переносимость в другой выпуск Ghidra и отсутствие оригинальных внешних путей **не проверялись**. В любом случае сырые xrefs/asm и vtable дампы сохранены отдельно от Ghidra database.

## Тесты в очищенном пакете

```bash
cd research/MCVar/05_COLLECTOR_FOUNDATION
PYTHONPATH=prototype python3 -m unittest discover -s tests -v
```

Наличие проходящих Python unit-тестов подтверждает только логику offline-модели. Исторические `PASS` из Stage16.7 Final требуют оригинальных DLL на машине агента; не переназывать их в `PASS` текущего окружения.
