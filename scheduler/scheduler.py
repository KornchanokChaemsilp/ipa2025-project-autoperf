import schedule
import time
import database  # <-- Import ไฟล์ database.py
import producer  # <-- Import ไฟล์ producer.py

# นี่คือ Queue ที่ iPerf Worker (Consumer) จะรอฟัง
IPERF_JOB_QUEUE = "iperf_job_queue"

def job():
    """
    งานที่จะทำทุก 10 วินาที
    """
    print("--- (Scheduler) เริ่มรอบการทำงาน ---")
    
    # 1. ดึงข้อมูล Router (IP, user, pass) จาก Mongo
    routers = database.get_all_routers()
    
    if not routers:
        print("--- (Scheduler) ไม่พบข้อมูล Router, สิ้นสุดรอบ ---")
        return

    # 2. ส่งข้อมูล Router (ทีละตัว) เข้า RabbitMQ
    for router in routers:
        # (คุณสามารถเพิ่มข้อมูลอื่นๆ ที่จำเป็นสำหรับ Worker ได้ที่นี่)
        job_data = {
            "ip": router.get("ip"),
            "username": router.get("username"),
            "password": router.get("password"),
            "task_type": "run_iperf"
        }
        producer.send_job_to_queue(job_data, IPERF_JOB_QUEUE)
    
    print(f"--- (Scheduler) ส่ง Job ทั้งหมด {len(routers)} งาน, สิ้นสุดรอบ ---")

# --- ส่วน main ---
if __name__ == "__main__":
    print("(Scheduler) เริ่มทำงาน... ตั้งค่างานทุก 10 วินาที")
    
    # ตั้งค่าให้ 'job()' ทำงานทุก 10 วินาที
    schedule.every(10).seconds.do(job)
    
    # รัน Job ครั้งแรกทันที (เพื่อทดสอบ)
    job() 

    # วนลูปเพื่อรัน 'schedule' ตลอดไป
    while True:
        schedule.run_pending()
        time.sleep(1)
