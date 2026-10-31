# Канонические адреса и идентификаторы MCVar

Справочник предназначен **только** для двух DLL с указанными SHA-256 и image base `0x10000000`. Адреса VA, не RVA; для RVA вычесть `0x10000000`. В будущих DLL использовать только после повторной привязки.

| Метод / interface | Old vtable target (VA) | New vtable target (VA) | Слот |
|---|---:|---:|---:|
| `IVar.ReadVarAsync` | `0x1000C3F6` | `0x1000C508` | 9 |
| `IVar.ReadVarCyclic` | `0x1000FAF0` | `0x1000FC02` | 11 |
| `IVar.RemoveCyclicVariables` | `0x10010BBB` | `0x10010CCD` | 12 |
| `IVar2.ReadVarAsync` | `0x1000C28A` | `0x1000C39C` | 9 |
| `IVar2.ReadVarCyclic` | `0x1000F93E` | `0x1000FA50` | 11 |
| `IVar2.RemoveCyclicVariables` | `0x10010A94` | `0x10010BA6` | 12 |

| Vtable | Old VA | New VA |
|---|---:|---:|
| `IVar` | `0x1002C5E4` | `0x1002D5F4` |
| `IVar2` | `0x1002C630` | `0x1002D640` |

**Проверка:** `03_REVERSE_ENGINEERING/entrypoints/iter2/VTABLE_MAP.json`, четыре `*_vtable_raw.txt`, `vtable_verification.json` и исходный `verify_vtables.py`. Проверено 12 слотов в среде агентов; полный аудит из архива требует оригинальных Siemens MCVar.dll.

## Callback-related call sites (не готовые API endpoint)

| Наблюдение | Old VA | New VA | Интерпретация |
|---|---:|---:|---|
| `IDispatch::GetIDsOfNames` call via `+0x14` | `0x1000FEF1` | `0x10010003` | разрешение `OnDataChanged`; **не доставка** |
| `IDispatch::Invoke`-shaped via `+0x18` | `0x100146A0` | `0x100147AA` | путь late-bound вызова; конкретная request provenance неизвестна |
| Typed-slot candidate via `+0x1C` | `0x10013AD2` | `0x10013BDC` | возможный `IReadVarAsyncCallback::OnDataChanged`; receiver не сопоставлен с `pCB` |
| Cyclic flush-region conditional helper | *(не установлен достоверный аналог)* | `0x100134AB -> 0x100139C2` | локальный прямой edge при флаге `0x80000`, не полный путь Cyclic |

**Не использовать в качестве точек входа:** old `0x1000D28A`, new `0x1000D39C`; в ранних заметках они ошибочно привязывались к слотам. Аналогично не использовать old `0x1001093E` как `IVar2.ReadVarCyclic` — это неверная транскрипция old `0x1000F93E`.

## Исследованные образы

- Old: SHA-256 `43a5c1991d98b6b6e155233a0114d7ff72bf4dec7edf58d0607da501e7d98712`, оригинальный путь `/root/PL/PCU_old/H/mmc2/MCVar.dll`.
- New: SHA-256 `5e7d955ebe7cfd52424b04e91471b7408f42bf6cc427e3d94c50bc7f4428c24a`, путь к MCVar внутри `/root/PL/PCU_new/.../F/mmc2/MCVar.dll` (полный путь в `01_CLIENT_CONTRACT/MCVAR_COM_ABI.json`).
