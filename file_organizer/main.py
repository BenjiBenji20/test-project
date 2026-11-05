import sys

from file_organizer.cmd.cmd import CMD
from file_organizer.cmd.navigator import ROOT_DIR, move_file, undo_move, redo_move
from file_organizer.cmd.helper_def import *
from file_organizer.application.file_organizer import FileOrganizerApp


def cmd_handler(cmd: str, organizer_app: FileOrganizerApp, rules: dict | None):
    """Handles chained command"""
    match cmd:
        # immediately exit the system
        case "exit":
            sys.exit()
        
        # List all the files in directory
        case "list":
            organizer_app.look_files_in_dir()
            
        # make file and folder pair rules {'.txt':'notes', ...}
        case "mkrules":
            new_rules = organizer_app.create_file_rules()
            return new_rules
        
        case "list-rules":
            organizer_app.display_rules(rules)
            return rules
            
        # organize file in directory
        case "org":
            if rules:
                move_file(organizer_app.path, rules)
            else:
                print("Make rules first using 'mkrules' command")
                return rules
            
        # undo command
        case "undo":
            undo_move()
            return rules
            
        # redo move
        case "redo":
            redo_move()
            return rules


def main():
    print("ORGANIZE YOUR FILE IN ONE COMMAND")
    print("Available Commands:")
    prompt = """
    - `goin <path>`: Navigate to the specified directory (like `cd`).
    - `org`: Organize files in the current directory—prompts for custom folder names based on detected extensions.
    - `undo`: Revert the last organization (if applicable).
    - `redo`: To redo the undid organization of files (if applicable).
    - `exit`: Exit the application (type anywhere to exit).
    - `list`: To display the available files in directory.
    - `mkrules`: To make file, folder pair rules.
    - `list-rules`: To display the current rules
    \n'Separate each by space for chain of commands'
    """
    print(prompt)
    print()
    
    current_dir = ROOT_DIR
    organizer_app = None
    path = ""
    rules = {}
    
    while True:
        if current_dir == ROOT_DIR and not organizer_app and not path:
            print("Navigate first in the directory using goin <patj> command.")
        
        cmd = input(str(f"\n\n{current_dir}>")).strip()
        
        if cmd.lower() == "exit":
            sys.exit()
        
        # check and handle if there is no command after goin <path>
        if is_chain_cmd(cmd):
            cmd_parts = cmd.split(" ")
            for i, c in enumerate(cmd_parts):
                if c == "goin":
                    if i + 1 < len(cmd_parts) and Path(ROOT_DIR / cmd_parts[i + 1]).exists(): # check for index boundary
                        path = rf"{cmd_parts[i + 1]}"
                        current_dir = str(rf"{ROOT_DIR}\{path}") # change current path for the user to know its current path
                        organizer_app = FileOrganizerApp(path)
                    elif not Path(ROOT_DIR / cmd_parts[i + 1]).exists():
                        print(f"Invalid path {cmd_parts[i + 1]}. Not exists.")
                    else:
                        print("'goin' command requires path")
                
                elif c in CMD or Path(c).exists(): # check if valid command 
                    if organizer_app:
                        res = cmd_handler(c, organizer_app, rules)
                        if res is not None:
                            rules = res
                    else:
                        print(f"tang ina Invalid command: {c}")
                        
                # Skip the path parameter for goin command
                elif cmd_parts[i-1] == "goin" if i > 0 else False:
                    continue
                
                else:
                    print(f"Invalid command in chain: {c}")
                
        # handle one command only if class has been initialized and path has value
        if organizer_app and path:
            res = cmd_handler(cmd, organizer_app, rules)
            if res is not None:
                rules = res
        else:
            print("Navigate first in the directory using goin <patj> command.")
            
    
if __name__ == "__main__":
    main()    
        
    