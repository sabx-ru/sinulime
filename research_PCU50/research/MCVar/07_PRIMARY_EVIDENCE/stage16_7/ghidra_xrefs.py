# Ghidra headless Python/Jython script: focused call/reference export.
from ghidra.program.model.symbol import RefType
from ghidra.program.model.address import Address
from java.io import PrintWriter

out = open(getScriptArgs()[0], 'w')
fm = currentProgram.getFunctionManager()
rm = currentProgram.getReferenceManager()
targets = [0x1000d28a,0x1000d39c,0x1000d7a4,0x1000d8b6,0x1000fef1,0x10010003,0x100146a0,0x100147aa,0x100134ab,0x100139c2,0x10011ba6]
for va in targets:
    addr = toAddr(va)
    out.write('\nTARGET %s %s\n' % (addr, getInstructionAt(addr)))
    for ref in rm.getReferencesTo(addr):
        fn = fm.getFunctionContaining(ref.getFromAddress())
        out.write('REF from=%s type=%s function=%s\n' % (ref.getFromAddress(), ref.getReferenceType(), fn.getEntryPoint() if fn else 'NONE'))
for fn in fm.getFunctions(True):
    if fn.getName().lower().find('cyclic') >= 0 or fn.getName().lower().find('readvarasync') >= 0 or fn.getName().lower().find('transactionid') >= 0:
        out.write('FUNC %s %s %s\n' % (fn.getEntryPoint(), fn.getName(), fn.getBody()))
out.close()
