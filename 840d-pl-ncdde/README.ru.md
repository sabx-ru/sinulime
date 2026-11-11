# Siemens 840D Powerline — исследование NCDDE

Независимая исследовательская программа для **однократного чтения** выбранных машинных данных SINUMERIK 840D Powerline через NCDDE на **PCU50 с Windows XP (x86)**.

**Состояние на 11.11.2026:** исходник собран на Debian и проверен на реальном PCU50. Восемь тестовых DDE-запросов завершились получением корректно оформленных бинарных ответов: Baseline, General/Channel/Axis MD и один Drive MD. Это не означает, что доступны все MD или что доказана индексация X/Y.

## Коротко: сборка и запуск

На Debian:

```bash
sudo apt install gcc-mingw-w64-i686-win32 binutils-mingw-w64-i686 file
./BUILD_DEBIAN.sh
```

Готовый файл: `windows/bin/ncdde_md_probe.exe`. Перенесите **всю** папку `windows` на PCU50. Начинайте с `RUN_00_BASELINE.cmd`; затем отдельно запускайте тесты General/Channel/Axis. Файлы результатов: `windows/logs/*.txt` (каждый ответ в новом TXT).

Важное ограничение: раньше после DDE-экспериментов фиксировались аварии приводов; их связь с запросами не доказана. **Не выполняйте тест Drive или произвольные адреса без оценки риска, разрешения оператора и безопасного состояния станка.** Программа не содержит запросов записи, но поведение серверной части нельзя гарантировать для любой машины.

## Что проверено на реальном PCU50

| Тип | Адрес | Ответ |
|---|---|---|
| Baseline | `/Nck/Configuration/numGlobMachAxes` | `2` |
| General TEA | `/acc/nc_tea/$MN_SYSCLOCK_CYCLE_TIME` | `0.004` |
| Channel TEA | `/acc/ch_tea/$MC_CHAN_NAME` | `CHAN1` |
| Axis TEA | `/acc/ax_tea/$MA_CTRLOUT_MODULE_NR` | `1` |
| General PRE | `/acc/nc_pre/$MN_SYSCLOCK_CYCLE_TIME` | `0.004` |
| Channel PRE | `/acc/ch_pre/$MC_RESET_MODE_MASK` | `0` |
| Axis PRE | `/acc/ax_pre/$MA_AX_MOTION_DIR` | `1` |
| Drive PRE | `/acc/vs_pre/$MD_MOTOR_NOMINAL_CURRENT` | `17.600000381469727` |

Номинальный ток не является текущим током привода. Значения принадлежат одному станку; соответствие всем экранам HMI, динамика данных, время обновления и индекс второй оси не проверены.

## Главные технические результаты

1. Рабочий запрос клиента: `DdeInitializeA → DdeConnect(ncdde, machineswitch) → DdeClientTransaction(XTYP_REQUEST, ncddeBinary) → DdeGetData`.
2. `slacx.dll` содержит карту префиксов `/acc/nc_tea/`, `/acc/ch_tea/`, `/acc/ax_tea/`, `/acc/drv_tea/` и метод `CreateNskFile` для формирования `LINK(...)`. Это **генерация описаний**, не чтение значения из NCU.
3. В оригинальных конфигурациях обнаружены определения General/Channel/Axis/Drive MD; 1 711 записей из трёх сохранённых `.NSK` прошли синтаксическую сверку с восстановленным шаблоном.
4. Код `dctl.ocx` содержит DDE-запрос и обработку ответа, однако сквозная цепочка от конкретного экрана HMI до этих вызовов **не доказана**.
5. Восемь бинарных пакетов можно независимо проверить без оборудования: `python3 tools/verify_frames.py`.

## Документация

- [English README](README.md)
- [Сборка и тестовые CMD](docs/build-and-run.md)
- [Протокол ответа NCDDE](docs/protocol.md)
- [Подробные результаты 8 тестов](docs/field-tests.md)
- [Реверс с адресами функций](docs/static-research.md)
- [Что доказано и что нет](docs/evidence-ledger.md)
- [Безопасность](docs/safety.md)
- [Повторение проверок](docs/reproduce.md)
- [План последующих исследований](docs/roadmap.md)
- [Проверка перед публикацией](docs/publication-checklist.md)

В репозиторий **не включены** оригинальные Siemens DLL/EXE, образ диска PCU50, полные файлы `.NSK`, полные трассы ProcMon/API Monitor и необезличенные журналы. См. `NOTICE.md`.
