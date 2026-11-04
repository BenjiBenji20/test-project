from file_organizer.cmd.helper_def import *
from file_organizer.cmd.navigator import *
import sys

class FileOrganizerApp:
    def __init__(self, path: Path):
        self.path = ROOT_DIR / path
        
        
    def look_files_in_dir(self):
        """Display available files in directory"""
        available_files = files_in_dir(self.path)
        if not available_files:
            print("No available files")
            return
            
        print("List of files: ")
        for values in available_files.values():
            for v in values:
                print(v)


    def create_file_rules(self) -> dict:
        """
        Create a key value pair for the chosem files and the available files
        ex:
            available files:
                ".txt": {"notes.txt", "todo.txt"},
                ".jpg": {"cat.jpg"}
            pair_rules passed param:
                {".jpg": "images", ".txt": "notes", ".py": "programs", ".png": "sugar"}
            directory name for each file extension [output]:
                {
                    ".jpg": "images", # <- .jpg stores in images folder
                    ".txt": "notes" # <- .txt stores in notes folder,
                    ... # .py and .png key, value were ignored since these files are not existing
                }
        """
        available_files = files_in_dir(self.path)
        if not available_files:
            print("No available files")
            return {}
        
        # Select file extensions available in directory
        print("List of available file extensions:")
        print(list(available_files.keys()))
        
        print("\nCreate file organization rules")
        print("(left file extension name, ex. .jpg, .txt,...) -> (right folder name). [case sensitive]")
        print("Type done if finish.")
        file_org_rules = {}
        while True:
            rule = input(str()).strip()
            if rule.lower() == "done":
                break
            
            if rule.lower() == "exit":
                sys.exit()
            
            if "->" not in rule or len(rule.split("->")) != 2:
                print("Rule not allowed")
            else:
                k, v = [r.strip() for r in rule.split("->")]
                if k in available_files.keys():
                    file_org_rules[k.strip()] = v.strip()
        
        print("\nSelected file rules: ")
        for k, v in file_org_rules.items():
            print(f"{k} : {v}")
            
        return file_org_rules
    

    def display_rules(self, rules: dict):
        print("File organization rules: [file extension:folder]")
        ls = []
        for k, v in rules.items():
            ls.append(f"{k} : {v}")

        print(ls)
        
        