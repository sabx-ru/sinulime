# Independent consolidation review

Verdict: ACCEPT the old ncdde serializer sequence stores and OEMTEXT dispatch, with the limits below. REJECT the current consolidated claim that no normal output writer/handle edge is recovered. REJECT any claim that the exact origin of error 0x85000903 has been established. Original binaries and other research files were not changed; this is a deletion/replacement nomination, not authorization to delete evidence.

## Scope and reproducibility

Fresh offline reads of PCU_old/H/mmc2/{ncdde.exe,MCVar.dll} and PCU_new/C/RECYCLER/S-1-5-21-4025392478-4199590385-3038547483-1005/Dc28/files/F/mmc2/{ncdde.exe,MCVar.dll}. The new copies are recycler/archive artifacts; their presence does not establish installed/runtime identity. GNU objdump 2.44, pefile 2024.8.26 and Capstone 5.0.7 were used. No vendor executable, live endpoint, or hash operation was run. /root/.instruments search returned no entries; no Ghidra work was needed. Raw instructions, PE sections, import names and scans are in research/logs_asmb/consolidation_reviewer.asm.

A parallel Hermes batch timed out before yielding output; direct bounded terminal calls succeeded. Bare python was absent; python3 succeeded. Neither issue invalidates the subsequent fresh evidence. Full requested old ranges 0x44A440..0x44AE80 and 0x449265..0x449520 were saved with objdump. Decoding a range from a mid-instruction boundary can produce spurious instructions; conclusions below use coherent sequences and independent Capstone decoding.

## 1. Sequence stores: ACCEPT static producer flow

The serializer's contiguous buffer starts at B=0x486BD0. Initialization at 0x44A5AA writes WORD [B]=0x14; 0x44A5B3 writes WORD [B+2]=DX; 0x44A5BA writes DWORD [B+0x10]=0xF6F7F8F9; 0x44A5C4 clears WORD [B+6]. These establish one concrete 20-byte header layout, rather than an unconnected bookkeeping word.

Old ncdde text VAs below map to raw file offsets VA-0x400000:

| VA | Raw offset | Exact bytes | Meaning |
|---|---|---|---|
| 0x44AA8A | 0x4AA8A | A0 84 68 48 00 | AL=BYTE [0x486884] |
| 0x44AA92 | 0x4AA92 | 66 0F B6 4C 24 20 | CX=zero-extended stack byte |
| 0x44AA98 | 0x4AA98 | 8A D0 | DL=AL |
| 0x44AA9A | 0x4AA9A | C1 E2 08 | shift EDX left 8 |
| 0x44AA9D | 0x4AA9D | 03 D1 | add ECX |
| 0x44AAA3 | 0x4AAA3 | 66 89 15 D6 6B 48 00 | WORD [B+6]=DX |
| 0x44AAB4 | 0x4AAB4 | FE C0 | increment AL modulo 256 |
| 0x44AAB7 | 0x4AAB7 | A2 84 68 48 00 | write next global byte |
| 0x44AABC | 0x4AABC | 89 15 D8 6B 48 00 | DWORD [B+8]=range/count result |
| 0x44AACA | 0x4AACA | A3 DC 6B 48 00 | DWORD [B+0xC]=size/result |

With s=current global byte and t=stack byte, WORD [B+6]=(s<<8)+t modulo 65536. Little-endian storage gives [B+6]=t and [B+7]=s. An exhaustive isolated Python test over all 256*256 byte pairs returned True for this packing identity. The pre-increment value is serialized; the increment is saved afterward. A branch guard at 0x44AA15/17, range checks and other branches control whether these instructions execute. Do not claim one increment per request or unconditional increment for every visited item.

Concrete producer/output bridge:

- 0x44A60A: E8 2C 7A FB FF calls 0x40203B; at raw 0x203B, E9 F0 86 04 00 jumps to serializer 0x44A730.
- 0x44A66E: 2D D0 6B 48 00 computes output length as cursor-B.
- 0x44A675: 68 D0 6B 48 00 pushes pSrc=B. Together with pushes at 0x44A673/674/67E/67F this passes format, length, buffer, handle slot and object to 0x4012F8.
- 0x44A680: E8 73 6C FB FF calls 0x4012F8; raw 0x12F8 contains E9 53 9A 04 00, jumping to 0x44AD50.
- 0x44AE20 pushes EBP=length; 0x44AE21 pushes ESI=pSrc; 0x44AE23: E8 2E C1 01 00 calls 0x466F56.
- 0x466F56/raw 0x66F56: FF 25 38 63 6C 00 jumps through IAT 0x6C6338, independently parsed as DdeCreateDataHandle. On the existing-handle path, 0x44AE5C calls the DdeAddData thunk instead.
- The serializer can also flush through 0x44AB2B -> 0x4012F8 with B and a computed size.

This proves an actual sequence byte in this old serializer's output header and an output-handle edge. It does not prove that a particular fixture/request used this branch, that MCVar owns the sequence, concurrency semantics, reset behavior, or a one-to-one correspondence with the 166 captures. Capture attribution still needs runtime/fixture-specific dataflow evidence.

PE qualification: old .data has RVA 0x76000, VirtualSize 0x24E0C4 and SizeOfRawData 0x9000. Both 0x486884 and 0x486BD0 lie in its virtual zero-filled tail, beyond the file-backed portion. pefile.get_data returns no raw bytes there. A nominal offset returned by get_offset_from_rva is not evidence of a stored zero byte. Loader zero initialization follows the PE layout; an explicit runtime reset was not established.

MCVar's separate outgoing stores remain valid: old 0x10003E10/new 0x10003E4F = 66 89 7B 06 (DI=0); old 0x10004630/new 0x1000466F = 66 C7 43 06 17 00; old 0x1000470E/new 0x1000474D = 66 C7 43 06 06 00. In these sections raw offset=VA-0x10000000. These constant request-side stores do not refute the ncdde response-side variable writer.

## 2. OEMTEXT dispatch: ACCEPT, with item comparison condition

0x449272 loads ESI=[EBP+0x0C], the format argument. 0x449275 compares 1; 0x44927C loads registered format WORD [0x499950]; 0x449283 compares it; 0x449287 (83 FE 07) compares format 7. TEXT and registered binary branch to 0x4492D3. Other formats reach the rejection helper at 0x4492C9.

The OEMTEXT branch additionally calls DdeCmpStringHandles at 0x449299 using [0x486864] and [0x4A6D18]. Thunk 0x466F26 is FF 25 1C 63 6C 00 through IAT 0x6C631C. A nonzero comparison result branches away at 0x4492A0. Thus this is a format-7 branch conditional on the special item handle matching; there is no integer item ordinal 7.

At 0x4492BD (raw 0x492BD), E8 94 DC 01 00 calls the same verified DdeCreateDataHandle thunk. Arguments: instance=[0x4A6CC0], pSrc=0x479C64, cb=6, offa=0, item=[0x486864], format=ESI=7, flags=0. EDI was zeroed at 0x448AF7 on this path. Source VA/raw 0x479C64/0x79C64 contains 4E 63 64 64 65 00, i.e. Ncdde plus NUL. This is concrete text content.

## 3. Error 0x85000903: origin NOT VERIFIED

A whole-file binary search for little-endian 03 09 00 85 returned zero matches in each of all four binaries. Executable-section Capstone scans found no immediate 0x85000903, 0x85000000 or 0x85000900. Additional immediate scans and nearby construction inspection did not recover a demonstrated construction yielding the requested error. Linear disassembly can confuse data tables and code, so this is a bounded negative finding, not proof that the error cannot be constructed or propagated from external input.

The proposed new MCVar target 0x10007DBD is coherent code, but it performs object cleanup: 56 8B 31 85 F6 74 0E, then ECX=ESI and a call at 0x10007DC6 (E8 09 00 00 00) to 0x10007DD4; it then frees/releases ESI through 0x10017ADC. The helper frees a nonempty string at [ESI+4] and replaces the pointer with 0x10038484 at 0x10007DEA. Old counterpart 0x10007CAF has the same cleanup shape. These bytes do not decode a header error or construct 0x85000903. Calling this target DecodeError/error origin based on nearby symbols is rejected. Reliable actual error decode and incoming-error dataflow remain open.

## 4. 0x420730 target: accept only local structure initialization

0x42075D/raw 0x2075D is C6 40 07 02, a constant [EAX+7]=2 store. It is guarded by input type 0x1A..0x1B. The routine writes through +0x27, so this is a larger structure; no direct relation to B=0x486BD0 or its DDE output was recovered. It cannot be used to infer that the actual serializer must overwrite a constant 2. Keep the raw instructions and local structure description; remove the packet-origin implication.

## 5. Exact deletion/replacement nominations (no deletions executed)

Line numbers refer to files read during this review; quote anchors should be used if concurrent edits move them.

### research/FINAL_REPORT.md

- Line 71 and line 200: delete the label `item 7`; replace with `CF_OEMTEXT format branch after special-item handle comparison`. Retain the verified call arguments.
- Line 94: delete the sentence beginning `The exact normal binary payload pointer, byte length, conversion routine, and final data-handle call remain unresolved.` Replace with the concrete B/cursor length and 0x44A680 -> 0x4012F8 -> 0x44AD50 -> 0x44AE23 path; retain unknown conversion semantics only where actually unresolved.
- Lines 123, 132 and 137..142: remove unqualified unknown-writer/type-alternative conclusions. State the static [B+7] writer is 0x44AAA3 with source 0x486884; capture-specific attribution and lifecycle remain unverified. Keep capture chronology only as separately sourced observations, not as independently reproduced here.
- Line 236: delete `This is the first confirmed response/header-like writer associated with the ncdde object family.` Retain the guarded larger-structure write and absence of demonstrated capture identity.
- Line 240: delete both sentences. The second sentence invents a required overwrite/copy relationship from the unrelated 0x420730 structure; the first ignores the actual output edge.
- Lines 243..246: delete the stale recovery tasks for a wholly unknown pointer/length/handle/writer. Replace with branch attribution to actual captures and sequence lifecycle investigation. Line 247 can remain as a capture-reconciliation task.
- Line 249: replace the blanket lack of a serializer/sequence-origin proof with the narrower distinction between verified static producer flow and unresolved capture-specific provenance.

### research/FINDINGS.md

- Line 55: replace `No later overwrite/copy into the captured 20-byte packet has yet been found.` with `No relationship between this larger structure and the serializer buffer B has been demonstrated.`
- Lines 64..66: delete the three blanket UNRESOLVED statuses; replace with static B/cursor-length/handle-edge/sequence-writer CONFIRMED and capture-specific attribution UNVERIFIED.

### Related misleading conclusions requiring the same correction

- research/findings/COUNTER_STATE_DATAFLOW.md line 33: delete the assertion that the file contains a stored zero byte at 0x486884; substitute virtual zero-filled tail evidence. Lines 66, 83..84: delete categorical absence of serializer-output dataflow; preserve capture attribution limits.
- research/evidence/phase9_reviewer_mcvar_ncdde_verdict.md lines 43 and 66: delete the claim that 0x486BD6 is disconnected bookkeeping; it is B+6. Keep limits about actual captures. Revise line 9's `once per visited serializer item/path` to `when the guarded sequence-store block executes`.
- research/MCVAR_REQUEST_CHAIN.md lines 113, 115 and task line 123: delete the requirement for a post-0x420730 overwrite; that structure's identity was never established. Substitute the verified serializer buffer bridge.
- research/FINAL_FINDINGS.md line 72: delete `ncdde.exe direct +0x06 writer: NOT FOUND`; the absolute-address store at 0x44AAA3 is B+6 even without a +6 displacement operand. Qualify the request-side MCVar conclusions at lines 68..74 so they do not reject a response sequence writer. Lines 94, 103, 108, 119 and 131: remove the semantic claim that old 0x10007CAF/new 0x10007DBD performs error decoding; the independently inspected code is cleanup. Do not erase the actual call evidence.

Preserve raw evidence and historical reports as audit records where useful. No whole-file deletion is justified by these findings. The substantive corrections concern stale conclusions and unsupported semantic labels.
