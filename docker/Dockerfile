FROM runpod/comfyui:latest

# Google Drive sync dependencies
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Sync script and entrypoint
COPY scripts/gdrive_sync.py /app/gdrive_sync.py
COPY scripts/entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

ENTRYPOINT ["/app/entrypoint.sh"]
