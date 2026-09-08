import typer
from typing import List, Optional, Dict
from phi.tools import Toolkit
from phi.utils.log import logger
from fabric import Connection
import uuid

class SSHTerminal(Toolkit):
    def __init__(self, id: str, hostname: str, username: str, password: Optional[str] = None, key_filename: Optional[str] = None):
        super().__init__(name="SSHTerminal")
        self.register(self.run_ssh_command)
        self.id = id
        
        # Prepare connect_kwargs dictionary
        connect_kwargs = {"password": password} if password else {}
        if key_filename:
            connect_kwargs["key_filename"] = key_filename
        
        self.connection = Connection(hostname, user=username, connect_kwargs=connect_kwargs)

    def run_ssh_command(self, commands: List[str]) -> str:
        """Runs a shell command over SSH and returns the output or error.
        
        Args:
            commands (List[str]): The commands to run as a list of strings.
        
        Returns:
            str: The output of the command.
        """
        try:
            logger.info(f"Running shell command with ID {self.id}: {' '.join(commands)}")
            result = self.connection.run(' && '.join(commands), hide=True)
            stdout = result.stdout
            return stdout
        except Exception as e:
            logger.warning(f"Failed to run shell command with ID {self.id}: {e}")
            return f"Error: {e}"

    def terminate(self):
        """Terminates the SSH connection."""
        self.connection.close()
        print(f"SSH terminal with ID {self.id} has been terminated.")

class SSHTerminalManager:
    def __init__(self):
        self.terminals: Dict[str, SSHTerminal] = {}

    def create_terminal(self, hostname: str, username: str, password: Optional[str] = None, key_filename: Optional[str] = None) -> str:
        """Creates a new SSHTerminal instance and returns its ID."""
        instance_id = str(uuid.uuid4())
        ssh_terminal = SSHTerminal(id=instance_id, hostname=hostname, username=username, password=password, key_filename=key_filename)
        self.terminals[instance_id] = ssh_terminal
        print(f"Created SSH terminal with ID: {instance_id}")
        return instance_id

    def run_command(self, terminal_id: str, commands: List[str]) -> str:
        """Runs a command on the specified terminal."""
        if terminal_id in self.terminals:
            result = self.terminals[terminal_id].run_ssh_command(commands)
            return result
        else:
            return f"No terminal found with ID: {terminal_id}"

    def terminate_terminal(self, terminal_id: str):
        """Terminates the specified terminal."""
        if terminal_id in self.terminals:
            self.terminals[terminal_id].terminate()
            del self.terminals[terminal_id]
        else:
            print(f"No terminal found with ID: {terminal_id}")

# Example usage:
if __name__ == "__main__":
    manager = SSHTerminalManager()
    
    # Create a new SSH terminal
    terminal_id = manager.create_terminal(hostname='HOSTNAME', username='USERNAME', password='PASSWORD')
    
    # Run a command on the created terminal
    output = manager.run_command(terminal_id, ['ls -a', 'uname -a'])
    print(output)
    
    # Terminate the SSH terminal
    manager.terminate_terminal(terminal_id)
