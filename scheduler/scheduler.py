import schedule
import time
import database  # <-- Import database.py (ไฟล์ด้านล่าง)
import producer  # <-- Import producer.py (ไฟล์ด้านบน)
import config  # <-- Import config.py (ไฟล์ด้านล่าง)

# ⬇️ [แก้ไข] อ่านชื่อคิวจาก config (ที่มาจาก .env)
IPERF_JOB_QUEUE = config.QUEUE_NAME  # (นี่คือ "iperf3_queue")


def job():
    """
    งานที่จะทำทุก 10 วินาที
    """
    print("--- (Scheduler) เริ่มรอบการทำงาน ---")

    # 1. ดึงข้อมูล Router (IP, user, pass) จาก Mongo
    # (ฟังก์ชันนี้จะอ่านจาก collection 'targets' ที่ถูกต้อง)
    targets = database.get_all_targets()

    if not targets:
        print(
            "--- (Scheduler) ไม่พบข้อมูล Router \
              (ใน collection 'targets'), สิ้นสุดรอบ ---"
        )
        return

    # 2. ส่งข้อมูล Router (ทีละตัว) เข้า RabbitMQ
    for router in targets:
        # (ดึงข้อมูลตามที่ Worker ต้องการ)
        job_data = {
            "ip": router.get("ip"),
            "username": router.get("username"),
            "password": router.get("password"),
        }
        # (ฟังก์ชันนี้จะใช้ Credentials ที่ถูกต้อง)
        producer.send_job_to_queue(job_data, IPERF_JOB_QUEUE)

    print(
        f"--- (Scheduler) ส่ง Job ทั้งหมด \
          {len(targets)} งาน, สิ้นสุดรอบ ---"
    )


# --- ส่วน main (เหมือนเดิม) ---
if __name__ == "__main__":
    # ตรวจสอบว่า config โหลดครบ
    if not config.QUEUE_NAME:
        print(
            "!!! [Scheduler Error] ไม่พบ QUEUE_NAME \
              ใน config, กรุณาตรวจสอบ .env"
        )
    else:
        print(
            f"(Scheduler) เริ่มทำงาน... ตั้งค่างานทุก \
              10 วินาที (ส่งไปที่คิว: {IPERF_JOB_QUEUE})"
        )

        # ตั้งค่าให้ 'job()' ทำงานทุก 10 วินาที
        schedule.every(10).seconds.do(job)

        # รัน Job ครั้งแรกทันที (เพื่อทดสอบ)
        print("(Scheduler) รันครั้งแรกทันที...")
        job()

        # วนลูปเพื่อรัน 'schedule' ตลอดไป
        while True:
            schedule.run_pending()
            time.sleep(1)
