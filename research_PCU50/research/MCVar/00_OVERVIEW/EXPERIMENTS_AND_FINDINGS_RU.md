# Исследования MCVar: техническое резюме и результаты экспериментов

**Объект:** Siemens SINUMERIK 840D PowerLine, COM API `MCVar.dll` (`IVar`, `IVar2`), два установленных образа PCU. Период Stage 15–16.7 Final: offline-исследования (31 октября 2026). Реальные измерения PCU относятся к более раннему исследованию Phase 14 и приведены как отдельный исторический источник.

## 1. Ответ на главный вопрос проекта

Мы намерены использовать **оригинальную библиотеку Siemens MCVar.dll**, а не воспроизводить её внутренний протокол. Статическое исследование установило методы и структуры COM-интерфейса, которые потребуются для Async/Cyclic, и создало проверяемую основу для клиента. Но **не доказало работоспособность callbacks и циклических подписок на реальной PCU**. Практически подтверждённым способом съёма данных остаётся пакетный `ReadVar`.

| Направление | Что реально установлено | Статус |
|---|---|---|
| `ReadVar` | Реальная PCU возвращала до 20 значений в одном вызове, с независимыми per-item quality/error | `HISTORICAL_RUNTIME_PROVEN` |
| `ReadVarAsync` | Exact TypeLib ABI, vtable slot 9 в обеих версиях IVar/IVar2 | `STATIC_PROVEN` (метаданные + адреса vtable), runtime не проверен |
| `ReadVarCyclic` | Exact TypeLib ABI, vtable slot 11, список/внутренние объекты циклических операций | `STATIC_PROVEN` частично, runtime не проверен |
| `RemoveCyclicVariables` | Подписанный метод, vtable slot 12; детали соответствия ReqID/removal и drain не доказаны | частично `STATIC_PROVEN`, семантика `UNKNOWN` |
| `OnDataChanged` | Две точные TypeLib-сигнатуры, кандидат прямого вызова и отдельный IDispatch-механизм | ABI `STATIC_PROVEN`; доставка `UNKNOWN` |
| TypeLib old/new | 28 TypeInfo и 92 объявленных метода в каждой библиотеке; 32 метода в восьми целевых TypeInfo | `STATIC_PROVEN` по декодированным TypeLib |
| Collector | Offline-прообраз корректно сохраняет last-good, выравнивает позиции, проверяет owner-thread | тесты offline; COM-клиент пока отсутствует |

## 2. Что показали реальные тесты PCU (контекст, *не* Stage 15–16.7)

Сохранённый ранее аудит Phase 14 описывает PCU50.3, Windows XP SP2 x86, реальный `MCVar.ReadVar` и сценарии read-only. В исходном пакете было 104 базовых и 309 дополнительных сценариев, **413 запусков зарегистрированы**, из них 12 не проверили целевую гипотезу из-за ошибок тестового пакета (отсутствующие probe, несовпадение параметров, запуск watchdog). Этим нельзя подтверждать Async/Cyclic.

Ключевые числа из аудита:

- 252 сценария MCVar, 277 вызовов `ReadVar`; 261 общих HRESULT=`0`, 16 HRESULT=`0x80020009`.
- 2 752 элемента с `quality=192`, 74 — с `quality=0`; 73 ошибки `0x81000303` на искусственно несуществующих адресах, одна `0x85000903` на `/Channel/Parameter/R[u1,100]`.
- В 272 из 277 вызовов `pTimeStamps` не дал пригодного source timestamp (`VT_ERROR`), в остальных пяти был `VT_EMPTY` для отклонённой формы массива. Источник времени для коллектора нужен собственный.
- Группы `ReadVar` размером 1, 5, 10, 15, 20 показали приблизительные медианы 35, 35, 60, 90, 115 мс по четырём сериям. Это наблюдаемая длительность в условиях тестовой PCU, а не гарантированный latency/SLA.
- Один общий HRESULT не говорит об успешности всех элементов; плохая форма SAFEARRAY может отклоняться до обработки, но частичные ошибки элементов и плохие адреса могут возвращаться при обработанном запросе.
- `cacheDevice` не продемонстрировал убедительного устойчивого выигрыша на имеющейся выборке.

Оригинальные PCU `.bin/.log` и исходные тестовые EXE/CMD остаются в ранее собранном отдельном `research/MCVar/experiments`. В этом архиве сохранены аудит и CSV-индексы (`09_PRIOR_PCU_TEST_INDEX/`), но **не скопированы все объёмные трассы**.

## 3. Stage 15 — базовая инвентаризация и offline-прототип

**Сделано:** идентифицированы две Siemens PE32 DLL; подтверждено присутствие ресурса `TYPELIB/1/1033` размером 19 732 байта; сформирован COM reference; написан небольшой Python collector core и 9 unit tests; получен Windows x86 `stage15_diag.exe` для проверки COM registration/TypeInfo, но не Async/Cyclic чтений.

**Ценность:** корректное разделение per-item ошибок, last-good, обновления, snapshot/freshness и проверка использования одного owner-thread. **Не путать:** это не полноценный Windows COM-адаптер и не доказанная циклическая подписка.

**Где:** `05_COLLECTOR_FOUNDATION/`, `07_PRIMARY_EVIDENCE/stage15/`, `08_HISTORY/stage15/`.

## 4. Stage 16 — восстановление TypeLib

Из двух оригинальных бинарных MSFT TypeLib декодированы GUID, `CC_STDCALL`, `memid`, vtable `oVft`, direction/optional flags, вложенные типы и callback-интерфейсы. Выделено 28 TypeInfo/версию и 92 прямых описания методов/версию. Сравнение восьми целевых интерфейсов old/new показывает одинаковые нормализованные описания.

**Прикладные сигнатуры:**

- `IVar2.ReadVarAsync`: `Names?`, `ServerHandles?`, `ClientHandles`, `CacheDevice`, `pCB`, `pDisp`, `[out] pReqID`, `[out,optional] pErrors`.
- `IVar2.ReadVarCyclic`: `Names?`, `ServerHandles?`, `ClientHandles`, `pCB`, `pDisp`, `Deadbands`, `RequestedUpdateRates`, `[out] pRevisedUpdateRates`, `[in,out] pReqID`, `[out,optional] pErrors`, `CriticalValues?`.
- `RemoveCyclicVariables`: `ReqID` и опциональные идентификаторы отдельных переменных/выходные ошибки. Параметры IVar и IVar2 отличаются: ориентироваться на JSON.
- `IReadVarAsyncCallback.OnDataChanged(Values, Qualities, ClientHandles)` — три входных `VARIANT`.
- `IReadVarAsyncCallback2.OnDataChanged(Values, TimeStamps, ClientHandles, Qualities?, ServerInfos?, Errors?)` — входные `VARIANT`, три последние optional. Это **не выходные** `VARIANT*` callback.

Полные типы/указатели/флаги и возврат `HRESULT` смотреть только в `01_CLIENT_CONTRACT/MCVAR_COM_ABI.json` и `02_TYPELIB/decoded/typelib_decode.json`, не в данном сокращённом перечне.

**Где:** `02_TYPELIB/` и `01_CLIENT_CONTRACT/`.

## 5. Stage 16.5 — первые внутренние пути

Из статических листингов появились следующие наблюдения:

- Указатель вызывающего кода `pReqID` передаётся в стартовую транзакцию и записывается в поле транзакции `+0x98` (само значение ID этим не раскрывается).
- В отдельной 12-байтовой обёртке хранится указатель на транзакцию по `+0x04`.
- Есть компоненты `CCyclic`, `CCyclicID`, `DataChange`, `IdleCB`, `FlushCyclics` и структуры списка. Их наличие не даёт целого гарантированного жизненного цикла подписки.
- Найдено локальное условное ребро на новой DLL `0x100134AB -> 0x100139C2` при флаге `0x80000` у owner `+0x28`; назначение всей цепочки остаётся неустановленным.

**Была ошибка:** вызов через `vtable+0x14` приняли за `OnDataChanged`; на следующем этапе он правильно распознан как `IDispatch::GetIDsOfNames`. Старое утверждение **опровергнуто**.

## 6. Stage 16.6 — корректировка и разделение механизмов callback

Установлены два разных участка:

1. `IDispatch::GetIDsOfNames("OnDataChanged")`: old `0x1000FEF1`, new `0x10010003`; смещение `+0x14` — **разрешение имени в DISPID**, не callback-доставка.
2. В иной функции `IDispatch::Invoke`-образный вызов с `+0x18`: old `0x100146A0`, new `0x100147AA`. Это доказательство наличия кода позднего связывания, но **не** доказательство, что конкретный `ReadVarAsync`/`ReadVarCyclic` успешно до него доходит.

Исправлен счёт методов **33 → 32** для восьми целевых TypeInfo. Показаны ограниченные структуры объекта Cyclic; алгоритмы rates/deadbands/critical не восстановлены.

## 7. Stage 16.7, итерация 2 — важнейший результат reverse

Восстановлены **реальные таблицы виртуальных методов** `IVar` и `IVar2` в обоих образах, подтверждённые COFF-символами и конкретными `.rdata` pointer words (12 соответствий для трёх методов × двух интерфейсов × двух DLL). Таблица в [CANONICAL_ADDRESSES_RU.md](CANONICAL_ADDRESSES_RU.md).

Промежуточные `0x1000D28A` old / `0x1000D39C` new — **не** адреса vtable для `IVar2.ReadVarAsync`; их нельзя использовать как COM entrypoint. Действительные указатели по vtable: `0x1000C28A` и `0x1000C39C` соответственно. Сходство строк не делает адрес валидной функцией.

Найден кандидат на прямой типизированный `OnDataChanged` через `call [ecx+0x1C]`: old `0x10013AD2`, new `0x10013BDC`. Смещение соответствует первому собственному методу dual callback после семи общих COM-слотов, **но происхождение receiver [ebx+0x10] от pCB не доказано**.

Структуры `ReqID` и Cyclic уточнены, но **нет** полного verified графа `ReadVarAsync → specific callback` и `DataChange → IdleCB → FlushCyclics → OnDataChanged`; механизма генерации numeric ReqID и отмены тоже нет.

## 8. Stage 16.7 Final — исправленный клиентский контракт

После устранения противоречий составлены семь актуальных файлов в `01_CLIENT_CONTRACT/`. В них разделены:

- доказанный *декларированный ABI* (TypeLib, IID, параметрический список, vtable);
- static-inferred/частичные COM call shapes;
- **не установленные runtime свойства**, для которых требуется реальная PCU.

**Активирующие метаданные:** CLSID `{8F64C6F2-C2A4-11D2-BFCA-00609792C500}`, ProgIDs `MCVar.Var2`, `MCVar.Var2.1` и алиасы; IVar IID `{C48394E0-EC79-11D0-99A9-00A0246D1792}`, IVar2 IID `{23EBEDE0-BD9B-11D1-BD5A-0080C7F7898A}`. Наличие регистрации в бинарном ресурсе не подтверждает успешный `CoCreateInstance` на целевой конфигурации.

**Инженерное следствие:** независимо от внутренних деталей Siemens можно строить polling collector; Async/Cyclic держать отключёнными до проверки `pCB`/`pDisp`, SAFEARRAY, регистрации/снятия подписки и доставки callbacks. Не интерпретировать `ReqID` как гарантированно пригодный removal key без runtime-доказательства.

## 9. Что доказано / чего ещё нет

### Достаточно подтверждено, чтобы не повторять исследование

- Обе версии DLL и соответствующие хеши/базовые адреса.
- Оригинальный TypeLib, GUID, список целевых COM-методов, типы/направления/порядок параметров и два callback интерфейса.
- Vtable slots 9 / 11 / 12, pointer values old/new на IVar и IVar2.
- Кодовые участки GetIDsOfNames, Invoke-shaped, typed-slot call-shaped и ограниченные офсеты транзакций.
- Историческая пригодность синхронных пакетов для чтения на PCU; semantics per-item errors.

### Не пытаться «додумывать» по static evidence

- Какие валидные SAFEARRAY и значения принимает Async/Cyclic в установленной PCU.
- Работает ли `ReadVarAsync` truly async и реально вызывает callback.
- Как выбрать `pCB` / `pDisp` и в какой поток пришлют уведомление.
- В каких единицах задаются `RequestedUpdateRates` и как сервер исправляет интервалы.
- Deadbands, CriticalValues, клиентские дескрипторы и точная форма callback payload.
- Автоматическое удаление подписок, истинная семантика `ReqID`, AddRef/Release и drain-barrier.
- Реальное поведение при reconnect, cancellation, slow callback, late callback, errors.

**Итог:** Широкий static reverse больше не является обязательным условием разработки. Следующая инвестиция усилий — практический read-only коллектор на `ReadVar`, архитектура Async/Cyclic как optional и целевые аппаратные тесты при доступе к PCU.
