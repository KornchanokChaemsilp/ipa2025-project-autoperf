# config.py
import os
import sys

# --- อ่านค่า Environment Variables ---
MONGO_URI = os.environ.get("MONGO_URI")
DB_NAME = os.environ.get("DB_NAME")
RABBITMQ_HOST = os.environ.get("RABBITMQ_HOST")
RABBITMQ_USER = os.environ.get("RABBITMQ_DEFAULT_USER")
RABBITMQ_PASS = os.environ.get("RABBITMQ_DEFAULT_PASS")
QUEUE_NAME = "iperf_job_queue"  # ชื่อคิวที่เราจะฟัง


def validate_config():
    """ตรวจสอบว่าตั้งค่า Environment Variables ที่จำเป็นครบ"""
    if not all([MONGO_URI, DB_NAME, RABBITMQ_HOST,
         RABBITMQ_USER, RABBITMQ_PASS]):
        print(
            "❌ [Worker] Error: MONGO_URI, DB_NAME, \
                RABBITMQ_HOST, RABBITMQ_DEFAULT_USER, \
                    และ RABBITMQ_DEFAULT_PASS ต้องถูกตั้งค่า"
        )
        sys.exit(1)
