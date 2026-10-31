import ghidra.app.script.GhidraScript;
import ghidra.program.model.symbol.Reference;
import ghidra.program.model.listing.Function;
import ghidra.program.model.address.Address;

public class ExportMCVarXrefs extends GhidraScript {
    public void run() throws Exception {
        if (getScriptArgs().length < 1) throw new Exception("output path required");
        java.io.PrintWriter out = new java.io.PrintWriter(getScriptArgs()[0]);
        long[] targets = {0x1000c28aL,0x1000c3f6L,0x1000f93eL,0x1000faf0L,0x10010a94L,0x10010bbbL,0x10010cbfL,0x100109ecL,0x10010a4dL,0x10011a94L,0x1000c39cL,0x1000c508L,0x1000fa50L,0x1000fc02L,0x10010ba6L,0x10010ccdL,0x10010dd1L,0x10010afeL,0x10010b5fL,0x10011ba6L,0x100134abL,0x100139c2L};
        for (long v : targets) {
            Address a = toAddr(v);
            out.println("TARGET " + a + " " + getInstructionAt(a));
            Reference[] refs = getReferencesTo(a);
            for (Reference r : refs) {
                Function f = getFunctionContaining(r.getFromAddress());
                out.println("REF from=" + r.getFromAddress() + " type=" + r.getReferenceType() + " function=" + (f == null ? "NONE" : f.getEntryPoint()));
            }
        }
        for (Function f : currentProgram.getFunctionManager().getFunctions(true)) {
            String n = f.getName().toLowerCase();
            if (n.contains("cyclic") || n.contains("readvarasync") || n.contains("transactionid") || n.contains("idle")) {
                out.println("FUNC " + f.getEntryPoint() + " " + f.getName() + " " + f.getBody());
            }
        }
        out.close();
    }
}
