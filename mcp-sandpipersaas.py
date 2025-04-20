#!/usr/bin/env python3
import os
import io
import zipfile
import shutil
import requests
from pathlib import Path
from typing import Optional, List
from mcp.server.fastmcp import FastMCP

# Initialize FastMCP server
mcp = FastMCP(name="mcp-sandpiperaas", timeout=100)

@mcp.tool()
def sandpiper_compile(
    top: str,
    f: Optional[List[str]] = None,
    o: Optional[str] = None,
    endpoint: Optional[str] = None,
    outdir: Optional[str] = None,

    # SandPiper no-M5 flags
    bestsv: bool = False,                # --bestsv
    clkAlways: bool = False,             # --clkAlways
    clkEnable: bool = False,             # --clkEnable
    clkGate: bool = False,               # --clkGate
    clkStageAlways: bool = False,        # --clkStageAlways
    compiler: Optional[str] = None,      # --compiler <vcs|modelsim|verilator>
    conversion: bool = False,            # --conversion
    debugSigs: bool = False,             # --debugSigs
    debugSigsGtkwave: bool = False,      # --debugSigsGtkwave
    debugSigsYosys: bool = False,        # --debugSigsYosys
    fmtDeclSingleton: bool = False,      # --fmtDeclSingleton
    fmtEscapedNames: bool = False,       # --fmtEscapedNames
    fmtFlatSignals: bool = False,        # --fmtFlatSignals
    fmtFullHdlHier: bool = False,        # --fmtFullHdlHier
    fmtInlineInjection: bool = False,    # --fmtInlineInjection
    fmtNoRespace: bool = False,          # --fmtNoRespace
    fmtPack: Optional[int] = None,       # --fmtPack <int>
    fmtPackAll: bool = False,            # --fmtPackAll
    fmtPackBooleans: bool = False,       # --fmtPackBooleans
    fmtStripUniquifiers: bool = False,   # --fmtStripUniquifiers
    fmtUseGenerate: bool = False,        # --fmtUseGenerate
    hdl: Optional[str] = None,           # --hdl <verilog|sv>
    iArgs: bool = False,                 # --iArgs
    inlineGen: bool = False,             # --inlineGen
    license: bool = False,               # --license
    licenseFile: Optional[str] = None,   # --licenseFile <path>
    noDirectiveComments: bool = False,   # --noDirectiveComments
    noline: bool = False,                # --noline
    nopath: bool = False,                # --nopath
    p: Optional[str] = None,             # --p <project>
    randomUnassigned: bool = False,      # --randomUnassigned
    reset0: bool = False,                # --reset0
    scrub: bool = False,                 # --scrub
    time: bool = False,                  # --time
    verbose: bool = False,               # --verbose
    xclk: bool = False,                  # --xclk
    xinj: bool = False,                  # --xinj

    # catch-all for any other flags
    additional_args: str = ""
) -> str:
    """
    Execute SandPiper-SaaS to compile from TL-Verilog(TLV) to SystemVerilog(SV).

    Parameters:
      top:                 Path to the top-level .tlv file.
      f:                   (Optional) list of include file paths.
      o:                   (Optional) output .sv filename override.
      endpoint:            (Optional) FaaS endpoint URL.
      outdir:              (Optional) extraction directory.
      bestsv (bool):        (Optional) Optimize the readability/maintainability of the generated SystemVerilog.
      clkAlways (bool):     (Optional) Use always-enabled clock strategy for deasserted 'when' conditions (no gating or enabling).
      clkEnable (bool):     (Optional) Use clock-enable strategy for deasserted 'when' conditions (applied as clock enables).
      clkGate (bool):       (Optional) Use gated-clock strategy for deasserted 'when' conditions (power-saving clock gating).
      clkStageAlways (bool):        (Optional) Apply gating/enabling only to the first flip-flop after each assignment, then free-running clock.
      compiler (Optional[str]):     (Optional) Target HDL compiler: 'vcs', 'modelsim', or 'verilator'.
      conversion (bool):        (Optional) Optimize output to support manual Verilog/SystemVerilog conversion.
      debugSigs (bool):     (Optional) Generate signals organized for optimal debug (copies per pipeline context).
      debugSigsGtkwave (bool):      (Optional) Alternate debug signal output avoiding GTKWave bugs.
      debugSigsYosys (bool):        (Optional) Alternate debug signal output optimized for Yosys.
      fmtDeclSingleton (bool):      (Optional) Declare each signal in its own statement with its own type.
      fmtEscapedNames (bool):       (Optional) Use escaped HDL names that closely mirror TLV names.
      fmtFlatSignals (bool):        (Optional) Declare all signals at top-level scope; no hierarchical references.
      fmtFullHdlHier (bool):        (Optional) Provide full HDL hierarchy for all scopes, including non-replicated.
      fmtInlineInjection (bool):        (Optional) Inline X-injection and recirculation assignments where possible.
      fmtNoRespace (bool):      (Optional) Preserve original whitespace; do not adjust alignment.
      fmtPack (Optional[int]):      (Optional) Pack signals to the given number of hierarchy levels.
      fmtPackAll (bool):        (Optional) Pack signals at all levels of hierarchy (overrides fmtPack).
      fmtPackBooleans (bool):       (Optional) Pack an additional level of hierarchy for boolean signals.
      fmtStripUniquifiers (bool):       (Optional) Eliminate uniquifiers in HDL names where possible.
      fmtUseGenerate (bool):        (Optional) Use generate/endgenerate keywords in SystemVerilog.
      hdl (Optional[str]):      (Optional) Target hardware description language: 'verilog' or 'sv'. Default sv. This is implicit if --p is given
      iArgs (bool):     (Optional) Process command-line arguments provided in the source file.
      inlineGen (bool):     (Optional) Produce generated code inline within the translated code.
      license (bool):       (Optional) Downgrade license permissions as instructed by Redwood EDA, LLC.
      licenseFile (Optional[str]):      (Optional) Path to license key file for Redwood EDA.
      noDirectiveComments (bool):       (Optional) Do not output comments on `line and `include directives.
      noline (bool):        (Optional) Disable `line directives in SV output.
      nopath (bool):        (Optional) Disable output of the distribution directory path.
      p (Optional[str]):        (Optional) Project name corresponding to configuration directory.
      randomUnassigned (bool):      (Optional) Provide random stimulus to unassigned signals ($random()).
      reset0 (bool):        (Optional) Apply *reset to all flip-flops, resetting them to zero.
      scrub (bool):     (Optional) Produce a scrubbed TL-X file representation.
      time (bool):      (Optional) Report program runtime to STDOUT (makes output unique).
      verbose (bool):       (Optional) Enable verbose debug output.
      xclk (bool):      (Optional) Enable X-injection on clock signals for gated/enabled logic.
      xinj (bool):      (Optional) Enable X-injection at pipesignal assignment statements.
      additional_args (str):        (Optional) Any other SandPiper flags not explicitly exposed above.
 
    Returns:
      Combined compile status, stdout/stderr, and extraction summary.
    """
    # 1) Defaults
    if endpoint is None:
        endpoint = "https://faas.makerchip.com/function/sandpiper-faas"

    top_path = Path(top)
    extraction_dir = str(top_path.parent.resolve()) if outdir is None else outdir
    default_file = top_path.with_suffix(".sv").name if o is None else o
    output_arg = default_file if outdir is None else os.path.join(outdir, default_file)

    # 2) Collect flags
    flags: List[str] = []
    if bestsv:            flags.append("--bestsv")
    if clkAlways:         flags.append("--clkAlways")
    if clkEnable:         flags.append("--clkEnable")
    if clkGate:           flags.append("--clkGate")
    if clkStageAlways:    flags.append("--clkStageAlways")
    if compiler:          flags += ["--compiler", compiler]
    if conversion:        flags.append("--conversion")
    if debugSigs:         flags.append("--debugSigs")
    if debugSigsGtkwave:  flags.append("--debugSigsGtkwave")
    if debugSigsYosys:    flags.append("--debugSigsYosys")
    if fmtDeclSingleton:  flags.append("--fmtDeclSingleton")
    if fmtEscapedNames:   flags.append("--fmtEscapedNames")
    if fmtFlatSignals:    flags.append("--fmtFlatSignals")
    if fmtFullHdlHier:    flags.append("--fmtFullHdlHier")
    if fmtInlineInjection:flags.append("--fmtInlineInjection")
    if fmtNoRespace:      flags.append("--fmtNoRespace")
    if fmtPack is not None:flags += ["--fmtPack", str(fmtPack)]
    if fmtPackAll:        flags.append("--fmtPackAll")
    if fmtPackBooleans:   flags.append("--fmtPackBooleans")
    if fmtStripUniquifiers:flags.append("--fmtStripUniquifiers")
    if fmtUseGenerate:    flags.append("--fmtUseGenerate")
    if hdl:               flags += ["--hdl", hdl]
    if iArgs:             flags.append("--iArgs")
    if inlineGen:         flags.append("--inlineGen")
    if license:           flags.append("--license")
    if licenseFile:       flags += ["--licenseFile", licenseFile]
    if noDirectiveComments:flags.append("--noDirectiveComments")
    if noline:            flags.append("--noline")
    if nopath:            flags.append("--nopath")
    if p:                 flags += ["--p", p]
    if randomUnassigned:  flags.append("--randomUnassigned")
    if reset0:            flags.append("--reset0")
    if scrub:             flags.append("--scrub")
    if time:              flags.append("--time")
    if verbose:           flags.append("--verbose")
    if xclk:              flags.append("--xclk")
    if xinj:              flags.append("--xinj")
    if additional_args:
        flags.extend(additional_args.split())

    # 3) Build the args field
    args_field = f"-i {top_path.name} -o {output_arg} {' '.join(flags)}"

    # 4) Create in‑memory zip of inputs
    zip_buffer = io.BytesIO()
    try:
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            if f:
                for fp in f:
                    zf.writestr(Path(fp).name, Path(fp).read_text(encoding='utf-8'))
            zf.writestr(top_path.name, top_path.read_text(encoding='utf-8'))
    except Exception as e:
        return f"Error creating input zip: {e}"

    # 5) POST to SandPiper FaaS
    payload = {
        'args': (None, args_field),
        'IAgreeToSLA': (None, "true"),
        'sv_url_inc': (None, "false"),
        'default_includes': (None, "false"),
        'context': ('context.zip', zip_buffer.getvalue())
    }
    try:
        response = requests.post(endpoint, files=payload, stream=True)
    except Exception as e:
        zip_buffer.close()
        return f"Error accessing compile service: {e}"
    zip_buffer.close()

    # 6) Extract and assemble outputs
    try:
        resp_zip = zipfile.ZipFile(io.BytesIO(response.content))
    except Exception as e:
        return f"Error extracting response zip: {e}"

    def _read(name: str) -> str:
        try:
            return resp_zip.open(name).read().decode('utf-8')
        except:
            return f"<Error reading {name}>"

    exit_code     = _read('status')
    stdout_output = _read('stdout')
    stderr_output = _read('stderr')

    # 7) Write files out
    compile_id = response.headers.get('compile_id')
    summary = ''
    if compile_id:
        for fn in resp_zip.namelist():
            if fn.startswith(f"{compile_id}/out/"):
                rel = os.path.relpath(fn, f"{compile_id}/out/")
                if rel.startswith('..'): continue
                tgt = os.path.join(extraction_dir, rel)
                os.makedirs(os.path.dirname(tgt), exist_ok=True)
                with resp_zip.open(fn) as src, open(tgt, 'wb') as dst:
                    shutil.copyfileobj(src, dst)
                summary += f"Extracted: {tgt}\n"
    else:
        summary = "No compile_id; no files extracted.\n"

    # 8) Return combined output
    return (
        f"Compile status: {exit_code}\n"
        f"STDOUT:\n{stdout_output}\n"
        f"STDERR:\n{stderr_output}\n"
        f"Files:\n{summary}"
    )

if __name__ == '__main__':
    mcp.run(transport='stdio')
