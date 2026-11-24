// Pre-analysis seeding for raw binaries: disassemble and create functions at
// caller-supplied entry addresses (hex). Thumb entries are given with a "t:" prefix.
// Usage: -preScript SeedEntries.java 0xADDR [t:0xADDR ...]
// @category ATM7039S
import ghidra.app.cmd.disassemble.ArmDisassembleCommand;
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;

public class SeedEntries extends GhidraScript {
    @Override
    public void run() throws Exception {
        for (String a : getScriptArgs()) {
            boolean thumb = a.startsWith("t:");
            Address addr = toAddr(Long.decode(thumb ? a.substring(2) : a));
            new ArmDisassembleCommand(addr, null, thumb).applyTo(currentProgram, monitor);
            createFunction(addr, null);
            addEntryPoint(addr);
        }
    }
}
