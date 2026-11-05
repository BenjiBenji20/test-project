from pathlib import Path
import shutil
import os
from .helper_def import org_file_in_dir

# start the navigation from root directory
# and define according to os type
# windows == nt, linux == /
ROOT_DIR = Path("C:\\") if os.name == "nt" else Path("/")


UNDO = [] # stack for undo
REDO = [] # stack for redo

def make_dir(path: Path, folders: list) -> list:
    """Create folders to specified path"""
    path = ROOT_DIR / path
    changes = []
    for f in folders:
        f_dir = path / Path(f)
        f_dir.mkdir(parents=True, exist_ok=True)
        changes.append(f_dir)
        
    return changes


def move_file(path: Path, rules: dict) -> bool:
    """Moves files and tracks the actions for undo and redo"""
    # Convert to absolute path
    if isinstance(path, str):
        path = Path(path)
    
    if not path.is_absolute():
        path = ROOT_DIR / path
    
    print(f"Organizing files in: {path}")
    
    # Check if directory exists
    if not path.exists():
        print(f"Error: Directory {path} does not exist")
        return False
    
    # Get organized files based on rules
    organized_files = org_file_in_dir(path, rules)
    
    if not organized_files:
        print("No files found that match the organization rules")
        return False
    
    # Create folders first
    folders = list(rules.values())
    make_dir(path, folders)
    
    # Track all changes for this bulk operation
    bulk_changes = []
    
    try:
        # Move files according to organization
        for folder_name, file_list in organized_files.items():
            destination_folder = path / folder_name
            
            for filename in file_list:
                source_path = path / filename
                dest_path = destination_folder / filename
                
                # Check if source file still exists
                if not source_path.exists():
                    print(f"File {source_path} no longer exists, skipping...")
                    continue
                
                # Check if destination already exists
                if dest_path.exists():
                    print(f"{dest_path} already exists, overwriting...")
                
                # Perform the move
                shutil.move(str(source_path), str(dest_path))
                
                # Track the change
                change = {
                    "file": filename,
                    "from": str(source_path),
                    "to": str(dest_path)
                }
                bulk_changes.append(change)
                print(f"Moved: {filename} -> {folder_name}/\n")
        
        # Add all changes as one bulk operation to undo stack
        if bulk_changes:
            UNDO.append(bulk_changes)
            REDO.clear()  # Clear redo stack when new operation is performed
            print(f"Successfully organized {len(bulk_changes)} files\n")
            return True
        else:
            print("No files were moved")
            return False
            
    except Exception as e:
        print(f"Error during file organization: {e}")
        return False
    

def undo_move() -> bool:
    "Undo the last bulk file move"
    if not UNDO:
        print("Nothing to undo")
        return False
    
    last_undo_operation = UNDO.pop() # hold the last operation from undo stack and remove it from there
    redo_operation = []
    folders_to_remove = set()
    
    try:
        # reverse the move from last operation
        for move in reversed(last_undo_operation):
            src_path = Path(move["to"])
            dest_path = Path(move["from"])
            
            if not src_path.exists():
                print(f"File from path: {src_path} not exists.")
                continue
            
            # ensure dest dir exists
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            
            # move back from previous operation
            shutil.move(str(src_path), str(dest_path))
            redo_operation.append(move) # track micro changes
            print(f"Undid changes to file: {move["file"]}")
            
            # trackk the parent folder only to be remove
            folders_to_remove.add(src_path.parent)
            # remove previous used empty folders
            for folder in folders_to_remove:
                try:
                    if folder.exists() and not any(folder.iterdir()): # check if empty, if true, then g
                        folder.rmdir()
                except OSError:
                    pass  # Folder not empty or other issue, skip
            
        if redo_operation:
            REDO.append(redo_operation)
            print("\nUndid successfully done\n")
            return True
        else:
            print("No files to undid")
            return False
        
    except Exception as e:
        print(f"Error during undo operaiton: {e}")
        UNDO.append(last_undo_operation) # put the operation back when failed
        return False


def redo_move() -> bool:
    """Redo the last bulk undo move"""
    if not REDO:
        print("Nothing to redo")
        return False
    
    last_redo_operation = REDO.pop() # hold the last operation from redo stack and remove it from there
    undo_operation = []
    
    try:
        # redo every move
        for move in last_redo_operation:
            src_path = Path(move["from"])
            dest_path = Path(move["to"])
            
            if not src_path.exists():
                print(f"File from path: {src_path} not exists.")
                continue
            
            # ensure dest dir exists
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            
            # move back again to the previous destination path
            shutil.move(str(src_path), str(dest_path))
            undo_operation.append(move) # hold the micro changes for undo stack
            print(f"Redid changes to file: {move["file"]}")
            
        if undo_operation:
            UNDO.append(undo_operation)
            print("\nRedid successfully done\n")
            return True
        else:
            print("No files to redid")
            return False
    
    except Exception as e:
        print(f"Error during redo operation: {e}")
        REDO.append(last_redo_operation) # put the operation back when failed
        return False
                
