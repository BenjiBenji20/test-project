# CLI File Organizer

A simple CLI tool to organize files in a directory by their extensions, moving them into user-customized folders. Built to demonstrate file handling and automation without frameworks.

## Features
- Navigate to a directory and organize files interactively in real-time, detecting changes during runtime.
- Supports custom folder names via user input for detected file extensions (e.g., `.jpg`, `.txt`, `.html`, `.mp4`).
- Automatically identifies available file types and only applies rules to existing extensions, ignoring irrelevant ones.
- Example: If directory has `.jpg` (e.g., "cat.jpg") and `.txt` (e.g., "notes.txt", "todo.txt"), you can pair them to custom folders like `.jpg` → `images`, `.txt` → `notes`.
- Supports undo and redo to revert the last organization.
- Supports chain of commands

## Commands
- `goin <path>`: Navigate to the specified directory (like `cd`).
- `org`: Organize files in the current directory—prompts for custom folder names based on detected extensions.
- `undo`: Revert the last organization (if applicable).
- `redo`: To redo the undid organization of files (if applicable).
- `exit`: Exit the application (type anywhere to exit).
- `list`: To display the available files in directory.
- `mkrules`: To make file, folder pair rules.
- `list-rules`: To display the current rules.
- `Separate each by space for chain of commands`

## Usage
1. Clone the repo and navigate to this folder.
2. Run the CLI app (e.g., `python main.py` or equivalent, depending on the language).
3. Use `goin <path>` to navigate to a directory with unorganized files.
4. Run `org` to detect files, input custom folder names for each extension, and sort accordingly.
5. Run `undo` to revert if needed.
6. Run `redo` to redo the undid commmand
7. Run `exit` to exit the application
8. Run `list` to display the available files in directory
9. Run `mkrules` to make file, folder pair rules
10. Run `list-rules` to display the current rules
11. `Separate each by space for chain of commands`
### Example commands: goin <path> list mkrules [you will be prompted to make file, folde pair rules] org undo redo list-rules

## Live Demo
- Running the app with minimal chain of commands
<p align="center">
  <a href="https://drive.google.com/file/d/1WrIZm5E3mgrjxKnUcl7EfxNyCa6PAgSP/view?usp=drive_link" target="_blank">
    <img width="750" height="984" alt="Image" src="https://github.com/user-attachments/assets/632998d1-d6ff-4d44-a18c-9e36629b03f1" width="600"/>
  </a>
</p>

- Running the app with multiple chain of commands
<p align="center">
  <a href="https://drive.google.com/file/d/195c1SY207vFL00CGbqWqeokBknQzeQX6/view?usp=drive_link" target="_blank">
    <img width="750" height="990" alt="Image" src="https://github.com/user-attachments/assets/17e269ef-c910-41cd-8bfc-fd729641b54b" width="600"/>
  </a>
</p>

*Note*: Focuses on real-time file detection and user-defined organization.
