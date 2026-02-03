import sys
if '/app' not in sys.path:
    sys.path.append('/app')

from app import create_app
from app.tasks.nvd import sync_nvd_task

app = create_app()

with app.app_context():
    print("Triggering NVD sync task (incremental)...")
    result = sync_nvd_task.delay(mode='incremental')
    print(f"Task triggered. Task ID: {result.id}")
