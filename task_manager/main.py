from task_manager.application.todo import Todo
from task_manager.application.todo_cmd import TodoCMD
import gc
import sys


def tasks_manager_app_command(action: str, todo: Todo):
    import json
    cmd = TodoCMD()
    
    match action:
        case "add task":
            tasks = cmd.add_task_command()
            added = todo.add_tasks(tasks)
            print(f"Task/s added {added}")
        case "update task progress":
            upd = cmd.update_progress_command()
            updated = todo.update_progress(id=upd["id"], mark=upd["mark"])
            print(f"Task progress updated {updated}")
        case "update task":
            id = int(input("Task ID: ").strip())
            task = todo.read_task(id)
            upd_t = cmd.update_task_command(task)
            updated = todo.update_task(upd_t)
            print(f"Task updated {updated}")
        case "delete task":
            id = int(input("Task ID: ").strip())
            deleted = todo.delete_task(id)
            print(f"Task deleted {deleted}")
        case "search tasks":
            keyword = input(str(">")).strip().lower()
            task_s = todo.search_task_by_keyword(keyword)
            if task_s:
                for t in task_s:
                    print(json.dumps(t, indent=2))
        case "view all tasks":
            all_tasks = todo.get_all_tasks()
            for task in all_tasks:
                print(json.dumps(task, indent=2))
            del all_tasks
            gc.collect()
        case _:
            print("Error found")
            

def main():
    print("Welcome Pythonese! This is a CLI Based Task Manager Application.\n\n")
    filename = None
    
    # START PROMPT FOR FILE
    decision = input(str("Use existing task file or create a new one? (u/c)\n>")).strip().lower()
    if decision == "exit":
        sys.exit()
    
    if decision == "u":
        # access fille dir 
        import os 
        tasks_dir = ".../task_manager/application/todo_data" # your own absolute path
        tasks_entries = os.listdir(tasks_dir) # list all existing json files 
        tasks_files = [file for file in tasks_entries if os.path.isfile(os.path.join(tasks_dir, file))] 
        
        if not tasks_files:
            print("No existing files found")
            
        print("Choose one:") 
        for file in tasks_files: 
            print(f"\t*{file}")

        while True:
            filename = input(str("\n>")).strip().lower()
            if filename == "exit":
                sys.exit()
            
            if filename not in tasks_files:
                print(f"No existing task file: {filename}")
            else:
                break
    else:        
        filename = input(str("Create filename.\n>"))
        if filename == "exit":
            sys.exit()
        
    todo_app = Todo(filename)
    actions = [
        "add task", "update task progress", 
        "update task", "delete task",
        "search tasks", "view all tasks"
    ]
    while True:
        print("\nType 'exit' to exit the Task Manager App.\n>")
        print("Choose action:")
        for a in actions:
            print(f"\t*{a}\n".capitalize())
            
        action = input(">").strip().lower()
        
        if action == "exit":
            break
        elif action not in actions:
            print(f"Action {action} not allowed")
            continue
        
        tasks_manager_app_command(action, todo_app)
    
    gc.collect()
    
if __name__ == "__main__":
    main()