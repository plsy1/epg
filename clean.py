#!/usr/bin/env python3
import os
import time
from datetime import datetime, timedelta
import re

# ---------------- 配置 ----------------
TARGET_DIR = "data"   # 要扫描的目录
DAYS_THRESHOLD = 10           # 超过多少天的文件会被删除
DELETE_FILES = True           # False = 只打印, True = 真正删除
# --------------------------------------

today = datetime.today()
threshold_date = today - timedelta(days=DAYS_THRESHOLD)

date_pattern = re.compile(r'(\d{8})')

total_files = 0
total_size = 0

if not os.path.exists(TARGET_DIR):
    print(f"Error: directory '{TARGET_DIR}' does not exist.")
    exit(1)

print(f"Scanning directory: {os.path.abspath(TARGET_DIR)}")
print(f"Deleting files older than {DAYS_THRESHOLD} days based on filename date\n")

for root, dirs, files in os.walk(TARGET_DIR):
    for file in files:
        match = date_pattern.search(file)
        if match:
            file_date_str = match.group(1)
            try:
                file_date = datetime.strptime(file_date_str, "%Y%m%d")
                if file_date < threshold_date:
                    file_path = os.path.join(root, file)
                    size = os.path.getsize(file_path)
                    print(f"[OLD] {file_path}, Date in filename: {file_date_str}, Size: {size} bytes")
                    total_files += 1
                    total_size += size
                    if DELETE_FILES:
                        os.remove(file_path)
            except ValueError:
                continue

print("\nSummary:")
print(f"Total files marked for deletion: {total_files}")
print(f"Total size: {total_size} bytes")
if not DELETE_FILES:
    print("\nNote: DELETE_FILES=False, no files were actually deleted. Set DELETE_FILES=True to delete them.")
