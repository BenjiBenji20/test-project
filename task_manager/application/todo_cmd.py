from typing import List
from datetime import datetime
from .todo import TaskMark

class TodoCMD:
    def __init__(self):
        pass
    
    def add_task_command(self) -> List[dict]:
        tasks: List[dict] = []
        
        while True:
            print("\nType 'exit' at any prompt to exit the Add Task Command Loop.")
            
            # Task Name
            task_name = input("Task Name: ").strip()
            if task_name.lower() == "exit":
                break

            # Task
            task_content = input("Task: ").strip()
            if task_content.lower() == "exit":
                break

            # Description
            description = input("Description: ").strip()
            if description.lower() == "exit":
                break

            # Deadline
            while True:
                deadline_input = input("Deadline (YYYY-MM-DD HH:MM:SS): ").strip()
                if deadline_input.lower() == "exit":
                    return tasks  # Exit immediately

                try:
                    deadline_dt = datetime.strptime(deadline_input, "%Y-%m-%d %H:%M:%S")
                    deadline = deadline_dt.strftime("%Y-%m-%d %H:%M:%S")
                    break
                except ValueError:
                    print("Invalid format! Please use YYYY-MM-DD HH:MM:SS")
            
            # Current timestamps
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            # Create task dictionary
            task = { 
                "id": None,
                "created_at": now,
                "updated_at": now,
                "task_name": task_name,
                "task": task_content,
                "description": description,
                "progress": TaskMark.PENDING.value,
                "deadline": deadline
            }
            
            tasks.append(task)
            print(f"Task '{task_name}' added successfully.")

            # Ask if user wants to continue
            cont = input("Add another task? (y/n): ").strip().lower()
            if cont != "y":
                break
            
        return tasks


    def update_progress_command(self) -> dict:
        print("\nType 'exit' at any prompt to exit the Update Progress Task Command Loop.")
        
        id = input(str("Task ID: ")).strip().lower()
        if id == "exit":
            return
        
        mark = input(
            str(f"[{TaskMark.DONE.value}, {TaskMark.PENDING.value}, {TaskMark.CANCELLED.value}]: ")
        ).strip().lower()
        if mark == "exit":
            return
        
        return {"id": int(id), "mark": mark}
    
    
    def update_task_command(self, current_task: dict) -> dict:
        while True:
            print("\nType 'exit' at any prompt to exit the Update Task Command Loop.")
            print("Leave blank if don't want to update specific key.")

            # Task Name
            task_name = input("Task Name: ").strip()
            if task_name.lower() == "exit":
                return {}

            # Task
            task_content = input("Task: ").strip()
            if task_content.lower() == "exit":
                return {}

            # Description
            description = input("Description: ").strip()
            if description.lower() == "exit":
                return {}
            
            # Prgress
            progress = input(
                str(f"[{TaskMark.DONE.value}, {TaskMark.PENDING.value}, {TaskMark.CANCELLED.value}]: ")
            ).strip()
            if progress.lower() == "exit":
                return {}

            # Deadline
            while True:
                deadline_input = input("Deadline (YYYY-MM-DD HH:MM:SS): ").strip()
                if deadline_input.lower() == "exit":
                    return {}

                if deadline_input == "":
                    deadline = current_task["deadline"]
                    break

                try:
                    deadline_dt = datetime.strptime(deadline_input, "%Y-%m-%d %H:%M:%S")
                    deadline = deadline_dt.strftime("%Y-%m-%d %H:%M:%S")
                    break
                except ValueError:
                    print("Invalid format! Please use YYYY-MM-DD HH:MM:SS")
            
            # Current timestamps
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            # Return updated task dictionary
            return { 
                "id": current_task["id"],
                "created_at": current_task["created_at"],
                "updated_at": now,
                "task_name": task_name if task_name else current_task["task_name"],
                "task": task_content if task_content else current_task["task"],
                "description": description if description else current_task["description"],
                "progress": progress if progress else current_task["progress"],  
                "deadline": deadline
            }

    
    