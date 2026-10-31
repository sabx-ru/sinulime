# Передача разработки: что делать дальше

## 1. Реальный MCVar-коллектор (базовая ветка)

Начинать с отдельного Windows x86 адаптера для **синхронного** `IVar2.ReadVar`, потому что его пакетное чтение уже наблюдалось на PCU. Не смешивать код COM с нормализацией, хранением состояния и UI.

Нужны слои:

1. **STA/COM worker** (консервативная политика реализации, а не доказательство типа callback-потока Siemens): init/create/read/release на owner-thread, при необходимости message pump.
2. **ReadVar adapter**: batches, per-item `HRESULT`, quality, error, raw `VARIANT`, локальные timestamps. Валидировать форму `SAFEARRAY` конкретного синхронного вызова по прежним тестам, не угадывать.
3. **Acquisition scheduler**: группы переменных и периоды чтения, backpressure, защита от зависших calls; timeout сам по себе не прерывает COM вызов и не даёт право освободить его память.
4. **Normalized state**: `last_good_value`, `last_good_at`, `observed_at`, `quality`, `freshness`, `slot_error`, `batch_hresult`. После BAD оставлять последнее GOOD, но явно помечать его устаревшим.
5. **Distribution/API/UI** (после стабильности транспортного адаптера): независимые consumer-подписки, NiceGUI — только отображение.

Сохранённый Stage 15 mock/offline collector — в `05_COLLECTOR_FOUNDATION/prototype/collector`; 9 unit tests — `05_COLLECTOR_FOUNDATION/tests`. Это **только основа**, COM интеграции ещё нет.

## 2. Experimental Async/Cyclic (изолированная ветка)

Объявленный COM контракт позволяет проектировать ABI-слой, но не гарантирует работающую доставку. Не включать native subscriptions по умолчанию на станке. Вызовы и их payload следует валидировать именно на целевой PCU и выпускать как capability-gated.

При следующем доступе к PCU выяснить минимально:

- CoCreateInstance/QueryInterface `IVar`/`IVar2` и реально выбранный callback1/callback2;
- какой `pCB`/`pDisp` принимает сервер, как проходит `QueryInterface`, `AddRef/Release`;
- какие SAFEARRAY/VARIANT, bounds, types допустимы для async/cyclic;
- доставляется ли `OnDataChanged`, с какими аргументами, на каком потоке, после какого времени, как ведёт себя при ошибке и изменениях качества;
- способ и срок получения usable `ReqID`, подтверждённый ключ для `RemoveCyclicVariables`, прекращение callbacks и cleanup;
- единицы `RequestedUpdateRates`, revised rates, deadbands/critical values, callbacks при неизменном значении;
- восстановление после сбоя и отсутствие небезопасного освобождения callback при поздней доставке.

Тесты должны быть **только read-only**, с выводом исходных `HRESULT`, VARIANT/SAFEARRAY metadata и монотонных timestamps; типизированные и dispatch callbacks различать специальными sentinel объектами. Этот архив **не включает новый Windows harness**, соответствующий Stage 16.7.

## 3. Чего больше не делать без новых данных

- Не повторять полный общий reverse MCVar или TypeLib.
- Не заниматься пока DDE/NCDDE или SolutionLine.
- Не переносить адреса между old/new без version-specific таблицы.
- Не считать `GetIDsOfNames` событием и не объявлять callback успехом по одному indirect-call instruction.
- Не выводить фактическую частоту Cyclic из наличия параметра `RequestedUpdateRates`.
- Не приписывать MCVar timestamp от станка: в реальных логах он обычно отсутствовал.

## 4. Документы разработчику (в порядке чтения)

1. `01_CLIENT_CONTRACT/MCVAR_CLIENT_CONTRACT.md`
2. `01_CLIENT_CONTRACT/MCVAR_COM_ABI.json`
3. `01_CLIENT_CONTRACT/CALLBACK_AND_LIFECYCLE.md`
4. `01_CLIENT_CONTRACT/COLLECTOR_INTEGRATION.md`
5. `01_CLIENT_CONTRACT/RUNTIME_UNKNOWNS.md`
6. `00_OVERVIEW/CANONICAL_ADDRESSES_RU.md`
7. `09_PRIOR_PCU_TEST_INDEX/PCU_PHASE14_AUDIT.md`

Дизассемблирование возобновлять только для точного нового вопроса, если PCU эксперимент обнаружит противоречие в контракте.
