import os
import pty
import select
import subprocess
import signal
import termios
import struct
import fcntl
import tty
from typing import Dict, Tuple

class AdvancedTerminal:
    def __init__(self):
        self.master, self.slave = pty.openpty()
        self.id = f"{os.getpid()}-{self.master}"
        self.process = subprocess.Popen(
            ['/bin/bash'],
            stdin=self.slave,
            stdout=self.slave,
            stderr=self.slave,
            preexec_fn=os.setsid,
            universal_newlines=True
        )

    def run_command(self, command: str) -> str:
        os.write(self.master, command.encode() + b'\n')
        return self._read_output()

    def _read_output(self) -> str:
        output = ""
        while True:
            r, _, _ = select.select([self.master], [], [], 0.1)
            if not r:
                break
            try:
                data = os.read(self.master, 1024).decode()
                if not data:
                    break
                output += data
            except OSError:
                break
        return output

    def get_id(self) -> str:
        return self.id

    def terminate(self):
        try:
            os.killpg(os.getpgid(self.process.pid), signal.SIGTERM)
            self.process.wait()
            os.close(self.master)
            os.close(self.slave)
            print(f"Terminal with ID {self.id} has been terminated.")
        except OSError as e:
            print(f"Error terminating terminal with ID {self.id}: {e}")

def get_terminal_size() -> Tuple[int, int]:
    with open(os.ctermid(), 'rb') as fd:
        size = struct.unpack('hh', fcntl.ioctl(fd, termios.TIOCGWINSZ, b'\0\0\0\0'))
    return size[1], size[0]  # columns, rows

def list_terminals(terminals: Dict[str, AdvancedTerminal]):
    if not terminals:
        print("No active terminals.")
    else:
        print("Active terminals:")
        for terminal_id in terminals:
            print(f"- {terminal_id}")

def main():
    terminals: Dict[str, AdvancedTerminal] = {}
    
    print("Welcome to the Advanced Terminal Execution Tool.")
    print("Available commands:")
    print("  create - Create a new terminal")
    print("  terminate <id> - Terminate a specific terminal")
    print("  run <id> <command> - Run a command on a specific terminal")
    print("  interact <id> - Interact with a specific terminal")
    print("  list - List all active terminals")
    print("  exit/quit - Exit the program")
    
    while True:
        try:
            command = input("Enter command: ").strip()
            if command.lower() in ['exit', 'quit']:
                print("Exiting shell.")
                break
            
            parts = command.split()
            if not parts:
                continue
            
            cmd_type = parts[0].lower()
            
            if cmd_type == "create":
                terminal = AdvancedTerminal()
                terminals[terminal.get_id()] = terminal
                print(f"Created terminal with ID: {terminal.get_id()}")
            
            elif cmd_type == "terminate":
                if len(parts) != 2:
                    print("Usage: terminate <id>")
                    continue
                terminal_id = parts[1]
                if terminal_id in terminals:
                    terminals[terminal_id].terminate()
                    del terminals[terminal_id]
                else:
                    print(f"No terminal found with ID: {terminal_id}")
            
            elif cmd_type == "run":
                if len(parts) < 3:
                    print("Usage: run <id> <command>")
                    continue
                terminal_id = parts[1]
                run_command = " ".join(parts[2:])
                if terminal_id in terminals:
                    result = terminals[terminal_id].run_command(run_command)
                    print(f"Output from terminal {terminal_id}:\n{result}")
                else:
                    print(f"No terminal found with ID: {terminal_id}")
            
            elif cmd_type == "interact":
                if len(parts) != 2:
                    print("Usage: interact <id>")
                    continue
                terminal_id = parts[1]
                if terminal_id in terminals:
                    terminal = terminals[terminal_id]
                    print(f"Interacting with terminal {terminal_id}. Press Ctrl+D to exit.")
                    old_settings = termios.tcgetattr(sys.stdin)
                    try:
                        tty.setraw(sys.stdin.fileno())
                        while True:
                            r, _, _ = select.select([sys.stdin, terminal.master], [], [])
                            if sys.stdin in r:
                                char = os.read(sys.stdin.fileno(), 1)
                                if not char or char == b'\x04':  # Ctrl+D
                                    break
                                os.write(terminal.master, char)
                            if terminal.master in r:
                                try:
                                    data = os.read(terminal.master, 1024)
                                    if not data:
                                        break
                                    sys.stdout.buffer.write(data)
                                    sys.stdout.flush()
                                except OSError:
                                    break
                    finally:
                        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
                    print("\nExited interactive mode.")
                else:
                    print(f"No terminal found with ID: {terminal_id}")
            
            elif cmd_type == "list":
                list_terminals(terminals)
            
            else:
                print("Unknown command. Use 'create', 'terminate <id>', 'run <id> <command>', 'interact <id>', or 'list'.")
        
        except KeyboardInterrupt:
            print("\nKeyboard interrupt detected. Use 'exit' or 'quit' to exit the program.")
        except Exception as e:
            print(f"An error occurred: {e}")

    # Cleanup: Terminate all active terminals
    for terminal in terminals.values():
        terminal.terminate()

if __name__ == "__main__":
    main()