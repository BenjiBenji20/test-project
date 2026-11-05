from enum import Enum
import json
from pathlib import Path
import random
from typing import List
import os
import gc

class TaskMark(Enum):
    DONE = "done"
    PENDING = "pending"
    CANCELLED = "cancelled"


class Todo:
    def __init__(self, filename: str):
        # handle file with different extension
        if os.path.splitext(filename)[1].lower() != ".json":
            filename = os.path.splitext(filename)[0] + ".json"
        # handle file with no extension
        if len(os.path.splitext(filename)) <= 1:
            filename += ".json"
            
        self.dir = Path(__file__).resolve().parents[0] / "todo_data"
        self.full_path = self.dir / filename
        
        if self.check_file_existence:
            print(f"Opening existing tasks in {filename}")
            self.write_tasks(self.get_all_tasks())
            gc.collect()
        
        self.task_keys = {
            "created_at", 
            "updated_at", "task_name",
            "task", "description",
            "progress", "deadline"
        }
        
    @property
    def check_file_existence(self) -> bool:
        return self.full_path.exists()
    
    
    # ACTION
    def add_tasks(self, tasks: List[dict]) -> int:
        """Add tasks to an existing tasks"""
        if len(tasks) == 0:
            return 0
        
        for item in tasks:
            if not self.task_keys.issubset(item.keys()):
                print("Lack of info. Removing item..")
                tasks.remove(item) # remove item if lack of key
                
            # avoid duplicate id by incrementing than current size of existing tasks
            item["id"] = [random.randint(1, 100) for _ in range(1)][0]
        
        # holds the tasks len after validations
        task_len = len(tasks)
        
        # get existing tasks and add the new one
        all_tasks = self.get_all_tasks()
        if all_tasks:
            tasks.append(all_tasks[0])
        
        # write the tasks to the json tasks file
        self.write_tasks(tasks)
                
        return task_len
        
    
    # ACTION
    def update_progress(self, id: int, mark: str) -> bool:
        if mark not in ["done", "pending", "cancelled"]:
            return False
        
        if self.check_file_existence:
            task = self.read_task(id)
            
            if task is None:
                return False
                
            task["progress"] = mark
        
        return True if self.update_task(task) else False
          
                
    def write_tasks(self, items: List[dict]) -> bool:
        try:
            self.dir.mkdir(parents=True, exist_ok=True) # create dir if not exists
            with open(self.full_path, 'w') as w:
                json.dump(items, w, indent=2)
                
            return True
        except Exception as e:
            print(f"Error writing tasks: {e}")
            return False
         
    
    def get_all_tasks(self) -> List[dict]:
        try:
            with open(self.full_path, "r") as r:
                return json.load(r)
        except Exception as e:
            print(f"Error reading all tasks: {e}")
            return []
    
                
    def read_task(self, id: int) -> dict:
        try: 
            # find task using id
            for task in self.get_all_tasks():
                if task["id"] == id:
                    return task
        except Exception as e:
            print(f"Task with id: {id} not found.")
            return {}
        
    
    # ACTION
    def update_task(self, task: dict) -> int:
        from datetime import datetime
        all_tasks = self.get_all_tasks()
        for i, t in enumerate(all_tasks):
            if t["id"] == task["id"]:
                task["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                all_tasks[i] = task
                break
        
        return 1 if self.write_tasks(all_tasks) else 0


    # ACTION
    def delete_task(self, id: int) -> int:
        all_tasks = self.get_all_tasks()
        d = 0
        for i, v in enumerate(all_tasks):
            if v["id"] == id:
                print(f"Task to be deleted: {v}")
                del all_tasks[i]
                d+=1
                break
        self.write_tasks(all_tasks)
        return d
    
    
    # ACTION
    def search_task_by_keyword(self, keyword: str) -> list:
        searched_tasks = []
        all_tasks = self.get_all_tasks()
        for task in all_tasks:
            if any(keyword.strip().lower() == str(v).strip().lower() for v in task.values()) or \
            any(keyword.strip().lower() == str(k).strip().lower() for k in task.keys()):
                searched_tasks.append(task)

        return searched_tasks
                