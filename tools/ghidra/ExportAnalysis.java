// Export a deterministic, non-decompiled summary of a Ghidra program as JSON.
// Records function entries/extents/call edges and scalar operands in a supplied
// address window (candidate MMIO references). Disassembly text and decompiler
// output are deliberately NOT exported, so results can be published without
// redistributing proprietary code.
//
// Script arguments (headless -postScript ExportAnalysis.java OUT [WIN_LO WIN_HI] [ENTRY ...]):
//   OUT     output JSON path
//   WIN_LO  window start (hex, default 0xb0000000)
//   WIN_HI  window end (hex, exclusive, default 0xb8000000)
// @category ATM7039S
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.*;
import ghidra.program.model.listing.*;
import ghidra.program.model.scalar.Scalar;
import ghidra.program.model.symbol.*;
import java.io.*;
import java.util.*;

public class ExportAnalysis extends GhidraScript {
    private static String hex(long v) { return String.format("\"0x%x\"", v); }

    @Override
    public void run() throws Exception {
        String[] args = getScriptArgs();
        if (args.length < 1) throw new IllegalArgumentException("output path required");
        long lo = args.length > 1 ? Long.decode(args[1]) : 0xb0000000L;
        long hi = args.length > 2 ? Long.decode(args[2]) : 0xb8000000L;
        Listing listing = currentProgram.getListing();
        FunctionManager fm = currentProgram.getFunctionManager();
        StringBuilder sb = new StringBuilder();
        sb.append("{\n \"format_version\": 1,\n \"tool\": \"ghidra ExportAnalysis.java\",\n");
        sb.append(" \"ghidra_version\": \"").append(getGhidraVersion()).append("\",\n");
        sb.append(" \"language\": \"").append(currentProgram.getLanguageID()).append("\",\n");
        sb.append(" \"image_base\": ").append(hex(currentProgram.getImageBase().getOffset())).append(",\n");
        sb.append(" \"window\": [").append(hex(lo)).append(", ").append(hex(hi)).append("],\n");
        sb.append(" \"functions\": [\n");
        boolean first = true;
        FunctionIterator it = fm.getFunctions(true);
        while (it.hasNext()) {
            if (monitor.isCancelled()) break;
            Function f = it.next();
            AddressSetView body = f.getBody();
            long insns = 0;
            TreeSet<Long> scalars = new TreeSet<>();
            InstructionIterator ii = listing.getInstructions(body, true);
            while (ii.hasNext()) {
                Instruction ins = ii.next();
                insns++;
                for (int i = 0; i < ins.getNumOperands(); i++) {
                    for (Object o : ins.getOpObjects(i)) {
                        if (o instanceof Scalar) {
                            long v = ((Scalar) o).getUnsignedValue();
                            if (v >= lo && v < hi) scalars.add(v);
                        }
                    }
                }
                for (Reference r : ins.getReferencesFrom()) {
                    if (r.getReferenceType().isData()) {
                        Data d = listing.getDataAt(r.getToAddress());
                        if (d != null && d.getValue() instanceof Scalar) {
                            long v = ((Scalar) d.getValue()).getUnsignedValue();
                            if (v >= lo && v < hi) scalars.add(v);
                        }
                    }
                }
            }
            TreeSet<Long> callees = new TreeSet<>();
            for (Function c : f.getCalledFunctions(monitor)) callees.add(c.getEntryPoint().getOffset());
            sb.append(first ? "" : ",\n");
            first = false;
            sb.append("  {\"entry\": ").append(hex(f.getEntryPoint().getOffset()));
            sb.append(", \"name\": \"").append(f.getName().replace("\"", "'")).append("\"");
            sb.append(", \"body_bytes\": ").append(body.getNumAddresses());
            sb.append(", \"instructions\": ").append(insns);
            sb.append(", \"thumb\": ").append(isThumb(f));
            sb.append(", \"calls\": [");
            sb.append(String.join(", ", callees.stream().map(ExportAnalysis::hex).toList()));
            sb.append("], \"window_constants\": [");
            sb.append(String.join(", ", scalars.stream().map(ExportAnalysis::hex).toList()));
            sb.append("]}");
        }
        sb.append("\n ]\n}\n");
        try (Writer w = new OutputStreamWriter(new FileOutputStream(args[0]), "UTF-8")) { w.write(sb.toString()); }
        println("exported " + fm.getFunctionCount() + " functions to " + args[0]);
    }

    private boolean isThumb(Function f) {
        var reg = currentProgram.getRegister("TMode");
        if (reg == null) return false;
        var v = currentProgram.getProgramContext().getValue(reg, f.getEntryPoint(), false);
        return v != null && v.intValue() == 1;
    }
}
