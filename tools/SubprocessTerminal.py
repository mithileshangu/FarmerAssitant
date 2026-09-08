import subprocess
import os
import shlex

class LocalTerminal:
    def __init__(self):
        self.id = None
        self.process = None

    def run_commands(self, commands, timeout=10):
        """
        Run a list of commands on terminal (Linux/Mac) or cmd (Windows).

        :param commands: List of commands to be executed.
        :type commands: list of str
        :param timeout: Time in seconds to wait for a command to complete before terminating it.
        :type timeout: int
        """
        if not isinstance(commands, list):
            raise ValueError("Commands should be provided as a list of strings.")

        combined_command = " && ".join(commands) if os.name == 'posix' else " & ".join(commands)
        
        try:
            if os.name == 'posix':  # Unix-like OS (Linux, MacOS, etc.)
                # Use shell=True to run the command in the shell
                self.process = subprocess.Popen(combined_command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            elif os.name == 'nt':  # Windows
                # On Windows, use shell=True to execute the command
                self.process = subprocess.Popen(combined_command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            else:
                raise OSError("Unsupported operating system")

            try:
                stdout, stderr = self.process.communicate(timeout=timeout)
            except subprocess.TimeoutExpired:
                self.process.kill()
                stdout, stderr = self.process.communicate()
                stderr += f"\nCommand '{combined_command}' timed out after {timeout} seconds."

            print(f"Combined Command: {combined_command}")
            print(f"Output: {stdout.strip()}")
            print(f"Error: {stderr.strip()} \n")
            if self.process.returncode != 0:
                print(f"Return code: {self.process.returncode}\n")


        except FileNotFoundError as e:
            print(f"Command not found: {combined_command}")
            print(f"Error: {str(e)} \n")
        except subprocess.CalledProcessError as e:
            print(f"An error occurred while executing command: {combined_command}")
            print(f"Return code: {e.returncode}")
            print(f"Output: {e.output}")
            print(f"Error: {e.stderr} \n")
        except Exception as e:
            print(f"An unexpected error occurred while executing command: {combined_command}")
            print(f"Error: {str(e)}")

# Example usage:
runner = LocalTerminal()
commands_to_run = [ "mkdir Tools",
"cd Tools",
"touch myfile1.txt" if os.name == 'posix' else "type nul > myfile1.txt"
"cd"
]

runner.run_commands(commands_to_run)
