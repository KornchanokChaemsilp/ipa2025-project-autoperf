import os
from pymongo import MongoClient

# อ่านค่า Config ที่ส่งมาจาก docker-compose
MONGO_URI = os.environ.get("MONGO_URI")
DB_NAME = os.environ.get("DB_NAME")

# ตรวจสอบว่ามี MONGO_URI หรือไม่
if not MONGO_URI:
    print("!!! [Error] ไม่พบ MONGO_URI")
    # (ควรจะ exit)
if not DB_NAME:
    print("!!! [Error] ไม่พบ DB_NAME")
    # (ควรจะ exit)

# เชื่อมต่อ MongoDB
try:
    client = MongoClient(MONGO_URI)
    db = client[DB_NAME]
    
    # Scheduler จะอ่านจาก Collection นี้
    # **หมายเหตุ**: คุณต้องสร้าง Collection นี้และใส่ข้อมูล (IP, user, pass) เองใน Mongo Compass
    router_collection = db.routers 
    
    print(f"(Scheduler-DB) เชื่อมต่อ MongoDB ที่ {DB_NAME} สำเร็จ")
except Exception as e:
    print(f"!!! [Error] (Scheduler-DB) ไม่สามารถเชื่อมต่อ MongoDB: {e}")

def get_all_routers():
    """
    ดึงข้อมูล Router (IP, user, pass) ทั้งหมดจาก Collection 'routers'
    """
    try:
        routers = list(router_collection.find({}, {"_id": 0})) # {} คือดึงทั้งหมด, {"_id": 0} คือไม่เอา _id
        print(f"(Scheduler-DB) ดึงข้อมูล Router {len(routers)} รายการ")
        return routers
    except Exception as e:
        print(f"!!! [Error] (Scheduler-DB) ไม่สามารถดึงข้อมูล Router: {e}")
        return []
