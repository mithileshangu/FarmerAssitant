import pexpect
import os
import signal
import sys
from typing import Dict

class Terminal:
    def __init__(self):
        self.shell = pexpect.spawn('/bin/bash', encoding='utf-8')
        self.shell.expect_exact('$')
        self.id = f"{self.shell.pid}-{self.shell.child_fd}"

    def run_command(self, command: str) -> str:
        self.shell.sendline(command)
        self.shell.expect_exact('$')
        return self.shell.before.strip()

    def get_id(self) -> str:
        return self.id

    def terminate(self):
        try:
            os.kill(self.shell.pid, signal.SIGTERM)
            self.shell.close()
            print(f"Terminal with ID {self.id} has been terminated.")
        except OSError as e:
            print(f"Error terminating terminal with ID {self.id}: {e}")

def list_terminals(terminals: Dict[str, Terminal]):
    if not terminals:
        print("No active terminals.")
    else:
        print("Active terminals:")
        for terminal_id in terminals:
            print(f"- {terminal_id}")

def main():
    terminals: Dict[str, Terminal] = {}
    
    print("Welcome to the Terminal Execution Tool.")
    print("Available commands:")
    print("  create - Create a new terminal")
    print("  terminate <id> - Terminate a specific terminal")
    print("  run <id> <command> - Run a command on a specific terminal")
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
                terminal = Terminal()
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
            
            elif cmd_type == "list":
                list_terminals(terminals)
            
            else:
                print("Unknown command. Use 'create', 'terminate <id>', 'run <id> <command>', or 'list'.")
        
        except KeyboardInterrupt:
            print("\nKeyboard interrupt detected. Use 'exit' or 'quit' to exit the program.")
        except Exception as e:
            print(f"An error occurred: {e}")

    # Cleanup: Terminate all active terminals
    for terminal in terminals.values():
        terminal.terminate()

if __name__ == "__main__":
    main()