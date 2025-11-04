import config  # Import config ของ scheduler เอง
from pymongo import MongoClient

# 1. เชื่อมต่อ MongoDB โดยใช้ URI จาก config
try:
    client = MongoClient(config.MONGO_URI)
    db = client[config.DB_NAME]

    # 2. ชี้ไปที่ Collection ที่ Web App บันทึกไว้
    targets_collection = db.targets

    print(f"(Scheduler) เชื่อมต่อ MongoDB ที่ {config.DB_NAME} สำเร็จ")
except Exception as e:
    print(f"!!! [Scheduler Error] ไม่สามารถเชื่อมต่อ MongoDB: {e}")

    # ถ้าเชื่อมต่อไม่ได้ ให้ใช้ collection จำลอง (ป้องกันการล่ม)
    class MockCollection:
        def find(self, *args, **kwargs):
            return []

    targets_collection = MockCollection()


def get_all_targets():
    """
    ดึงข้อมูล Target ทั้งหมดจาก targets_collection
    (ฟังก์ชันนี้คือสิ่งที่ main.py เรียกใช้)
    """
    try:
        # 3. คืนค่าเป็น List of dicts
        return list(targets_collection.find({}, {"_id": 0}))
    except Exception as e:
        print(
            f"!!! [Scheduler Error] \
               ไม่สามารถดึงข้อมูลจาก targets_collection: {e}"
        )
        return []
