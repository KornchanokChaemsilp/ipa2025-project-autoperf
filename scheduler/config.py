import os

# 1. อ่านค่า Config ทั้งหมดจาก Environment Variables (ที่ .env ส่งมา)
MONGO_URI = os.environ.get("MONGO_URI") 
DB_NAME = os.environ.get("DB_NAME")
RABBITMQ_HOST = os.environ.get("RABBITMQ_HOST")

RABBITMQ_USER = os.environ.get("RABBITMQ_DEFAULT_USER")
RABBITMQ_PASS = os.environ.get("RABBITMQ_DEFAULT_PASS")

QUEUE_NAME = "iperf_job_queue"

# 2. ตรวจสอบว่าได้ค่าครบ
if not all([MONGO_URI, DB_NAME, RABBITMQ_HOST, RABBITMQ_USER, RABBITMQ_PASS]):
    print("!!! [Scheduler Error] ไม่พบ Environment Variables ที่จำเป็นทั้งหมด")
    # (ในความเป็นจริง เราควรจะ sys.exit(1) ที่นี่)