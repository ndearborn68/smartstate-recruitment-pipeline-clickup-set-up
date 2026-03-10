import os
import json, subprocess, time

CLICKUP_TOKEN = os.environ.get("CLICKUP_API_TOKEN", "YOUR_CLICKUP_TOKEN")

lists = {
    '901414417498': 'Senior Flutter Developer',
    '901414414372': 'Mid-Level Flutter Developer', 
    '901414414435': 'Senior Product Manager',
}

total_deleted = 0

for list_id, name in lists.items():
    print(f"\n--- {name} (list {list_id}) ---", flush=True)
    
    # Get all tasks with pagination
    all_tasks = []
    page = 0
    while True:
        result = subprocess.run([
            'curl', '-s',
            f'https://api.clickup.com/api/v2/list/{list_id}/task?page={page}&include_closed=true&subtasks=true',
            '-H', f'Authorization: {CLICKUP_TOKEN}'
        ], capture_output=True, text=True, timeout=30)
        
        data = json.loads(result.stdout)
        tasks = data.get('tasks', [])
        if not tasks:
            break
        all_tasks.extend(tasks)
        page += 1
        time.sleep(0.5)
    
    print(f"  Found {len(all_tasks)} total tasks", flush=True)
    
    # Group by email custom field
    seen_emails = {}
    duplicates = []
    
    for task in all_tasks:
        email = None
        for cf in task.get('custom_fields', []):
            if cf.get('name') == 'Email':
                email = cf.get('value', '')
                break
        
        if email:
            if email in seen_emails:
                # Keep the first one (older), delete this duplicate
                duplicates.append(task['id'])
            else:
                seen_emails[email] = task['id']
        else:
            # No email - check by name
            task_name = task.get('name', '')
            if task_name in seen_emails:
                duplicates.append(task['id'])
            else:
                seen_emails[task_name] = task['id']
    
    print(f"  Found {len(duplicates)} duplicates to delete", flush=True)
    
    batch_count = 0
    deleted = 0
    for tid in duplicates:
        result = subprocess.run([
            'curl', '-s', '-X', 'DELETE',
            f'https://api.clickup.com/api/v2/task/{tid}',
            '-H', f'Authorization: {CLICKUP_TOKEN}'
        ], capture_output=True, text=True, timeout=30)
        deleted += 1
        batch_count += 1
        
        if deleted % 50 == 0:
            print(f"  Deleted {deleted}/{len(duplicates)}", flush=True)
        
        if batch_count >= 95:
            print(f"  Rate limit pause...", flush=True)
            time.sleep(62)
            batch_count = 0
        else:
            time.sleep(0.65)
    
    total_deleted += deleted
    print(f"  Done: deleted {deleted} duplicates", flush=True)

print(f"\n=== DEDUP COMPLETE: {total_deleted} duplicates removed ===", flush=True)
