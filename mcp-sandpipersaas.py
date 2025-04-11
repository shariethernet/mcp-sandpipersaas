from mcp.server.fastmcp import FastMCP

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


@mcp.tool()
def convert_tlv_to_sv(input_path: str, output_directory: str = None) -> str:
    """
    Converts a TLV file to SV using sandpiper-saas.
    Args:
        input_path (str): Path to the input TLV file.
        output_directory (str, optional): Path to the output directory. Defaults to the same directory as the input file.
    """
    import os
    import subprocess
    import shutil

    input_tlv_file_path = os.path.abspath(input_path)
    if output_directory is None:
        output_file_path = os.path.dirname(input_tlv_file_path)
    else:
        output_file_path = os.path.abspath(output_directory)
    print(f"Input TLV file path: {input_tlv_file_path}")
    print(f"Output directory: {output_file_path}")
    if shutil.which("sandpiper-saas") is None:
        try:
            subprocess.run(["pip", "install", "sandpiper-saas"], check=True)
        except subprocess.CalledProcessError as e:
            return f"Error: sandpiper-saas installation failed: {e}"

    command = f"sandpiper-saas -i {input_tlv_file_path} -o {output_file_path}.sv"
    try:
        subprocess.run(command, shell=True, check=False,capture_output=True, cwd=os.path.dirname(input_tlv_file_path))
    except subprocess.CalledProcessError as e:
        return f"Error: sandpiper-saas execution failed: {e}"
    #return f"{res.stderr}\n{res.stdout}"
    return f"TLV file converted to SV successfully"


if __name__ == "__main__":
    # Initialize and run the server
    mcp.run(transport='stdio')
    #convert_tlv_to_sv("D:\\mcp-sandpipersaas\\example\\1_adder.tlv")
