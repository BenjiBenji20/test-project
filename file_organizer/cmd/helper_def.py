from pathlib import Path
import os

# Functions designed to always call files_in_dir, which then navigate to pass param path directory.
# files_in_dir organizes the files in key, value pair {extension: filename}.
# It was designed this way to handle real-time changes of files in the pass param path directory during code runtime.


# start the navigation from root directory
# and define according to os type
# windows == nt, linux == /
ROOT_DIR = Path("C:\\") if os.name == "nt" else Path("/")

def files_in_dir(path: Path) -> dict:
    """Collects existing files in dir"""
    path = ROOT_DIR / path
    files = [f for f in path.iterdir() if f.is_file()]

    res = {}
    for file in files:
        file_extension = file.suffix.lower()
        if file_extension not in res:
            res[file_extension] = set() 
        res[file_extension].add(file.name)
        
    return res
    
    
def org_file_in_dir(path: Path, rules: dict) -> dict:
    """Organize files in directory according to rules"""
    organized = {}
    path = ROOT_DIR / path
    
    if not path.exists():
        return {}
    
    # Get all files in the directory not included the subdirectories
    files = [f for f in path.iterdir() if f.is_file()]
    
    for file in files:
        file_extension = file.suffix.lower()

        # Check if this extension has a rule
        for ext, folder in rules.items():
            if file_extension == ext.lower():
                if folder not in organized:
                    organized[folder] = []
                organized[folder].append(file.name)
                break
    
    return organized
    
    
def is_chain_cmd(cmd: str) -> bool:
    import re
    return re.search(r"\s", cmd) or cmd != cmd.strip()
