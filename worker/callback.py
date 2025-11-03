# callback.py
import json
import datetime

# Import โมดูลที่ต้องใช้ในการประมวลผล
from database import db_collection
from ansible import run_ansible_and_iperf

def callback(ch, method, properties, body):
    """
    ฟังก์ชันที่จะถูกเรียกอัตโนมัติเมื่อมี "งาน" เข้ามาจาก RabbitMQ
    """
    data = {}
    try:
        data = json.loads(body.decode('utf-8'))
        ip = data.get("ip")
        user = data.get("username")
        password = data.get("password")

        if not all([ip, user, password]):
            print(f"❌ [Worker] ข้อความไม่สมบูรณ์: {body}")
            ch.basic_ack(delivery_tag=method.delivery_tag)
            return

        # --- 3. ทำงานจริง (เรียกใช้จาก ansible.py) ---
        iperf_result_str = run_ansible_and_iperf(ip, user, password)
        iperf_result_json = json.loads(iperf_result_str)

        # --- 4. บันทึกผลลง MongoDB (ใช้ db_collection จาก database.py) ---
        db_entry = {
            "router_ip": ip,
            "timestamp": datetime.datetime.now(datetime.timezone.utc),
            "test_data": iperf_result_json
        }
        db_collection.insert_one(db_entry)
        print(f"✅ [Worker] บันทึกผลของ {ip} ลง MongoDB เรียบร้อย")

        # --- 5. ส่งสัญญาณ "เสร็จสิ้น" (เฉพาะเมื่อสำเร็จ) ---
        print(f"  [Ack] ยืนยันการทำงาน {ip} กลับไปที่ RabbitMQ")
        ch.basic_ack(delivery_tag=method.delivery_tag)

    except Exception as e:
        # --- 6. ถ้าล้มเหลว ---
        print(f"❌ [Worker] ❗❗ เกิดข้อผิดพลาดในการประมวลผล {data.get('ip')}: {e}")
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
        print(f"  [Nack] ส่งงาน {data.get('ip')} ที่ล้มเหลวทิ้ง")
    
    print(f"--- ☕ [Worker] รองานต่อไป ---")