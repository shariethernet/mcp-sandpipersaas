from mcp.server.fastmcp import FastMCP
from typing import Optional, List
import os
import io
import zipfile
import requests
import shutil
from pathlib import Path
mcp = FastMCP(name="mcp-sandpiperaas", timeout=100)

@mcp.tool()
def calculator(a: int, b: int, operation: str) -> float | str:
    """
    Perform a calculation based on the provided operation.
    Supported operations: add, subtract, multiply, divide.
    Args:
        a (int): First number.
        b (int): Second number.
        operation (str): Operation to perform (add, subtract, multiply, divide).
    Returns:
        float | str: Result of the calculation.
    """
    if operation == "add":
        result = a + b
    elif operation == "subtract":
        result = a - b
    elif operation == "multiply":
        result = a * b
    elif operation == "divide":
        if b == 0:
            return "Error: Division by zero is not allowed."
        result = a / b
    else:
        return "Error: Unsupported operation."
    return result


# @mcp.tool()
# def convert_tlv_to_sv(input_path: str, output_directory: str = None) -> str:
#     """
#     Converts a TLV file to SV using sandpiper-saas.
#     Args:
#         input_path (str): Path to the input TLV file.
#         output_directory (str, optional): Path to the output directory. Defaults to the same directory as the input file.
#     """
#     import os
#     import subprocess
#     import shutil

#     input_tlv_file_path = os.path.abspath(input_path)
#     if output_directory is None:
#         output_file_path = os.path.dirname(input_tlv_file_path)
#     else:
#         output_file_path = os.path.abspath(output_directory)
#     # print(f"Input TLV file path: {input_tlv_file_path}")
#     # print(f"Output directory: {output_file_path}")
#     if shutil.which("sandpiper-saas") is None:
#         try:
#             subprocess.run(["pip", "install", "sandpiper-saas"], check=True)
#         except subprocess.CalledProcessError as e:
#             return f"Error: sandpiper-saas installation failed: {e}"

#     command = f"sandpiper-saas -i {input_tlv_file_path} -o {output_file_path}.sv"
#     try:
#         res = subprocess.run(command, shell=True, check=False,capture_output=True, cwd=os.path.dirname(input_tlv_file_path))
#     except subprocess.CalledProcessError as e:
#         return f"Error: sandpiper-saas execution failed: {e}"
#     return f"{res.stderr}\n{res.stdout}"
#     #return f"TLV file converted to SV successfully"

@mcp.tool()
def sandpiper_compile(
    top: str,
    f: Optional[List[str]] = None,
    o: Optional[str] = None,
    endpoint: Optional[str] = None,
    outdir: Optional[str] = None,
    sv_url_inc: bool = False,
    default_includes: bool = False,
    additional_args: str = ""
) -> str:
    """
    Execute the SandPiper-SaaS compile that converts TL-Verilog (TLV) files to SystemVerilog (SV).
    This function automatically accepts the Terms of Service and handles file extraction.
    
    Parameters:
      top (str): Path to the top-level TLV file.
      f (Optional[List[str]]): List of include file paths. Leave empty if it is not provided by the user
      o (Optional[str]): Output file name for SystemVerilog output (*.sv). Leave empty if it is not provided by the user
                         If not provided, defaults to the input filename but with a .sv extension.
      endpoint (Optional[str]): Compile service endpoint URL. Leave empty if it is not provided by the user
      outdir (Optional[str]): Directory where output files will be extracted. Leave empty if it is not provided by the user
                           If not provided, defaults to the directory of the input file.
      sv_url_inc (bool): Whether to request the 'sv_url_inc' directory.Leave empty if it is not provided by the user
      default_includes (bool): Whether to get default include files.Leave empty if it is not provided by the user
      additional_args (str): Additional arguments to pass to SandPiper.Leave empty if it is not provided by the user
    
    Returns:
      str: A combined message that includes the service exit code, stdout/stderr output, and details
           of any extracted files.
    """
    # Automatically accept Terms of Service without user prompt.
    home: Path = Path.home()
    tos_file: Path = home / ".makerchip_accepted"
    tos_file.touch(exist_ok=True)
    tos_message: str = f"Terms of Service accepted (recorded in: {tos_file}).\n"

    # Set default endpoint if not provided.
    if endpoint is None:
        endpoint = "https://faas.makerchip.com/function/sandpiper-faas"

    # Determine the extraction directory.
    # If outdir is not provided, use the directory of the input file.
    top_path: Path = Path(top)
    if outdir is None:
        extraction_dir: str = str(top_path.parent)
        print(f"Default extraction directory: {extraction_dir}")
    else:
        extraction_dir = outdir

    # Determine the output file name (for the '-o' flag).
    # If o is not provided, use the input file name with a .sv extension.
    if o is None:
        default_file_name: str = top_path.with_suffix(".sv").name
        print(f"Default file name: {default_file_name}")
    else:
        default_file_name = o

    output_file_arg = os.path.join(extraction_dir, default_file_name)
    print(f"Output file name: {output_file_arg}")
    # Build the compile service argument string.
    tlv_output: str = f"-o {output_file_arg}"
    args_field: str = f"-i {top_path.name} {tlv_output} {additional_args}".strip()

    # Create a zip archive (in memory) containing the input files.
    zip_buffer: io.BytesIO = io.BytesIO()
    try:
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
            # Add include files (if any).
            if f is not None:
                for file_path in f:
                    try:
                        with open(file_path, 'r', encoding='utf-8') as file_obj:
                            content: str = file_obj.read()
                        zip_file.writestr(Path(file_path).name, content)
                    except Exception as e:
                        return f"Error processing include file '{file_path}': {e}"
            # Add the top-level file.
            try:
                with open(top, 'r', encoding='utf-8') as file_obj:
                    top_content: str = file_obj.read()
                zip_file.writestr(top_path.name, top_content)
            except Exception as e:
                return f"Error processing top-level file '{top}': {e}"
    except Exception as e:
        return f"Error creating input zip archive: {e}"

    # Build the payload for the POST request.
    payload: dict = {
        'args': (None, args_field),
        'IAgreeToSLA': (None, "true"),
        'sv_url_inc': (None, "true" if sv_url_inc else "false"),
        'default_includes': (None, "true" if default_includes else "false"),
        'context': ('context.zip', zip_buffer.getvalue())
    }

    try:
        response: requests.Response = requests.post(
            endpoint,
            files=payload,
            stream=True
        )
    except Exception as e:
        return f"Error accessing compile service: {e}"
    finally:
        zip_buffer.close()

    # Process the received zip response.
    try:
        response_zip: zipfile.ZipFile = zipfile.ZipFile(io.BytesIO(response.content))
    except Exception as e:
        return f"Error extracting the response zip: {e}"

    # Retrieve the output streams.
    try:
        stderr_output: str = response_zip.open('stderr').read().decode('utf-8')
    except Exception as e:
        stderr_output = f"Error reading stderr: {e}"
    try:
        stdout_output: str = response_zip.open('stdout').read().decode('utf-8')
    except Exception as e:
        stdout_output = f"Error reading stdout: {e}"
    try:
        exit_code: str = response_zip.open('status').read().decode('utf-8')
    except Exception as e:
        exit_code = f"Error reading exit code: {e}"

    # Extract output files (if any) to the specified extraction directory.
    compile_id: Optional[str] = response.headers.get("compile_id")
    extraction_summary: str = ""
    if compile_id is not None:
        for file_name in response_zip.namelist():
            if file_name.startswith(f"{compile_id}/"):
                # Compute relative path.
                rel_path: str = os.path.relpath(file_name, f"{compile_id}/out/")
                if rel_path.startswith(".."):
                    continue  # Ignore unexpected files.
                target_path: str = os.path.join(extraction_dir, rel_path)
                os.makedirs(os.path.dirname(target_path), exist_ok=True)
                try:
                    with response_zip.open(file_name) as source_file, open(target_path, "wb") as target_file:
                        shutil.copyfileobj(source_file, target_file)
                    extraction_summary += f"Extracted file: {target_path}\n"
                except Exception as e:
                    extraction_summary += f"Error extracting file '{target_path}': {e}\n"
    else:
        extraction_summary = "No compile_id found in response headers; no files were extracted.\n"

    # Prepare the combined return message.
    combined_output: str = (
        tos_message +
        f"Compile service exit code: {exit_code}\n" +
        "Standard Output:\n" + stdout_output + "\n" +
        "Standard Error:\n" + stderr_output + "\n" +
        "Extraction Summary:\n" + extraction_summary
    )
    return combined_output

if __name__ == "__main__":
    # Initialize and run the server
    mcp.run(transport='stdio')
    # a = convert_tlv_to_sv("D:\\mcp-sandpipersaas\\example\\1_adder.tlv")
    # print(a)
    # Uncomment to test directly
    # input_file_path = "D:\\mcp-sandpipersaas\\example\\1_adder.tlv"
    # out = sandpiper_compile(top=input_file_path)
    # print(out)
