from phi.assistant import Assistant
from phi.llm.groq import Groq
import json
import io
import contextlib
import json
import io
import contextlib

class PythonRepl:
    def __init__(self):
        pass

    def run_code(self, code: str) -> str:
        """Execute the provided Python code and return the output.

        Args:
            code (str): Python code to execute.

        Returns:
            str: Output of the executed code.
        """
        # Create a string IO stream to capture the output
        output_stream = io.StringIO()
        
        # Redirect stdout to the string IO stream
        with contextlib.redirect_stdout(output_stream):
            try:
                exec(code)
            except Exception as e:
                return json.dumps({"error": str(e)})
        
        # Get the output from the string IO stream
        output = output_stream.getvalue()
        return json.dumps({"output": output})
