#!/bin/bash

# cd to the root dir to clear the path
cd / 
# cd again to the root dir of runnable python code
cd /c/Users/your_username/path_to_main.py_file

# activate venv (optional)
source venv/Scripts/activate # (bash)

# run the python script
py -m file_organizer.main


# better to put this in environment variable (on windows)
# with PREREQUISITE you should have wsl installed in your machine  :>
# 1. just copy the path for the root dir of the main.py (just until the file_organizer dir dont copy with child dir)
# 2. put in your system's path variable
# 3. close any cmd environment (bash, cmd, shell, etc...)
# 4. open again your cmd environment (bash, cmd, shell, etc...)
# 5. file_organizer.sh
