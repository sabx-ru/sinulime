# Исправленные ошибки агентов и устаревшие трактовки

Использовать при передаче задачи новым агентам, чтобы не повторять ошибочные выводы.

| Старое утверждение | Исправление | Источник |
|---|---|---|
| Вызов `+0x14` (`0x1000FEF1` old) непосредственно вызывает `OnDataChanged` | Это `IDispatch::GetIDsOfNames`; `Invoke` находится в отдельном участке через `+0x18` | `03_REVERSE_ENGINEERING/corrections/stage16_6/STAGE16_5_CORRECTIONS.md` |
| В восьми целевых TypeInfo 33 метода | Прямо объявлены **32**; 92 — во всех 28 TypeInfo/версию. Наследуемые IDispatch слоты сюда не добавляются | Stage 16.6 correction и `02_TYPELIB/` |
| `0x1000D28A` old / `0x1000D39C` new — настоящие vtable entrypoints IVar2.ReadVarAsync | Правильные слоты указывают `0x1000C28A` / `0x1000C39C`. Два прежних адреса — candidate interior/shared blocks, а не COM slot targets | `03_REVERSE_ENGINEERING/entrypoints/iter2/VTABLE_MAP.json` |
| `IVar2.ReadVarCyclic` old = `0x1001093E` | Правильно `0x1000F93E`; старый адрес — неверная транскрипция | `08_HISTORY/stage16_7/ITERATION2_EVIDENCE_CORRECTIONS.md` |
| Совпадающие адреса Ghidra/Rizin автоматически доказывают границы `DataChange` / `IdleCB` | Некоторые символические метки попадают на внутренние/неверно декодированные блоки. Нужны xrefs и подтверждение исходными байтами | Stage 16.6 corrections и Stage 16.7 acceptance |
| `TimeStamps`, `Qualities`, `Errors` в callback2 являются `[out] VARIANT*` | **Входные `VARIANT`**, три optional (`Qualities`, `ServerInfos`, `Errors`); `TimeStamps` обязательный `[in]` | `01_CLIENT_CONTRACT/MCVAR_COM_ABI.json` |
| `pReqID` всегда output и безопасен как removal key | `ReadVarAsync`: `[out] VT_I4*`; `ReadVarCyclic`: `[in,out] VT_I4*`. Способ и момент использования при снятии подписки неизвестны | `01_CLIENT_CONTRACT/COLLECTOR_INTEGRATION.md` |
| Прямой `call [ecx+0x1C]` — подтверждённый callback конкретного запроса | Это убедительный **кандидат по типу слота**, но receiver `[ebx+0x10]` не сопоставлен с переданным `pCB` | `01_CLIENT_CONTRACT/RUNTIME_UNKNOWNS.md` |
| Все 413 Phase 14 сценариев доказали поведение целевых механизмов | 413 сценариев были зарегистрированы; **12 не проверили гипотезу** из-за тестовых дефектов, Async/Cyclic ни одним из этих тестов не подтверждены | `09_PRIOR_PCU_TEST_INDEX/PCU_PHASE14_AUDIT.md` |

## Правило источников

1. Для сигнатур/IID/flags: бинарный TypeLib, `01_CLIENT_CONTRACT/MCVAR_COM_ABI.json`.
2. Для COM entrypoint: `03_REVERSE_ENGINEERING/entrypoints/iter2/VTABLE_MAP.json` и сырые `.rdata`.
3. Для callback и lifetime: `01_CLIENT_CONTRACT/CALLBACK_AND_LIFECYCLE.md` с отметками `UNKNOWN`, а не ранние этапы.
4. Для поведения PCU: только реальные логи в ранее созданном `research/MCVar/experiments` (в этом архиве — аудит и индексы).
5. `08_HISTORY/` — контекст исследования, **не канонические сведения**, если отличаются от более поздних проверок.
