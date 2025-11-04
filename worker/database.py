# db.py
import time
from pymongo import MongoClient
import config  # Import จากไฟล์ config.py ของเรา


def get_mongo_connection():
    """เชื่อมต่อ MongoDB (พยายามต่อใหม่เรื่อยๆ ถ้าล่ม)"""
    while True:
        try:
            client = MongoClient(config.MONGO_URI, serverSelectionTimeoutMS=5000)
            client.server_info()  # ทดสอบการเชื่อมต่อ
            mydb = client[config.DB_NAME]
            mycol_results = mydb["iperf3_results"]
            print("✅ [Worker] เชื่อมต่อ MongoDB สำเร็จ")
            return mycol_results
        except Exception as e:
            print(f"❌ [Worker] ไม่สามารถเชื่อมต่อ MongoDB: {e}. กำลังลองใหม่ใน 5 วินาที...")
            time.sleep(5)


# เชื่อมต่อทันทีเมื่อ import module นี้
# ไฟล์อื่นสามารถ import db_collection ไปใช้ได้เลย
db_collection = get_mongo_connection()
