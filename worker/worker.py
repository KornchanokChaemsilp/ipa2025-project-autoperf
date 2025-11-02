import os
import sys
import pika
import time
import json
import datetime
import subprocess
from pymongo import MongoClient

# --- 1. อ่านค่า Environment Variables ---
MONGO_URI = os.environ.get("MONGO_URI")
DB_NAME = os.environ.get("DB_NAME")
RABBITMQ_HOST = os.environ.get("RABBITMQ_HOST")
QUEUE_NAME = "router_queue" # ชื่อคิวที่เราจะฟัง

# --- 2. เชื่อมต่อ MongoDB (พยายามต่อใหม่เรื่อยๆ ถ้าล่ม) ---
def get_mongo_connection():
    while True:
        try:
            client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
            client.server_info() # ทดสอบการเชื่อมต่อ
            mydb = client[DB_NAME]
            mycol_results = mydb["interface_status"]
            print("✅ [Worker] เชื่อมต่อ MongoDB สำเร็จ")
            return mycol_results
        except Exception as e:
            print(f"❌ [Worker] ไม่สามารถเชื่อมต่อ MongoDB: {e}. กำลังลองใหม่ใน 5 วินาที...")
            time.sleep(5)

mycol_results = get_mongo_connection()


def run_ansible_and_iperf(ip, user, password):
    """
    ฟังก์ชันหลัก: รัน Ansible (ติดตั้ง) และ iperf3 client (ทดสอบ)
    """
    print(f"▶️ [Worker] เริ่มทำงานกับ {ip}...")
    
    # --- ขั้นตอน A: รัน Ansible Playbook ---
    # (ติดตั้ง iperf3 และ รัน iperf3 -s บนเครื่องเป้าหมาย)
    playbook_path = "ansible/playbook.yaml"
    config_path = "ansible/ansible.cfg"

    # ตั้งค่า Environment Variable ANSIBLE_CONFIG ชั่วคราว
    # เพื่อให้ ansible-playbook รู้ว่าต้องใช้ config ไฟล์ไหน
    env = os.environ.copy()
    env["ANSIBLE_CONFIG"] = config_path

    ansible_cmd = [
        "ansible-playbook",
        "-i", f"{ip},",  # ระบุ IP เป้าหมาย (inventory)
        playbook_path,
        # ส่งตัวแปร (user, pass) ให้ Ansible
        "--extra-vars", f"ansible_user={user} ansible_ssh_pass={password} ansible_become_pass={password}"
    ]
    
    print(f"  [Ansible] ติดตั้ง/เริ่ม iperf3 server บน {ip}...")
    # รันคำสั่ง ansible-playbook
    process_ansible = subprocess.run(ansible_cmd, env=env, capture_output=True, text=True) 
    
    if process_ansible.returncode != 0:
        # ถ้า Ansible ล้มเหลว (เช่น รหัสผ่านผิด, SSH ไม่ได้)
        print(f"❌ [Ansible] ล้มเหลวสำหรับ {ip}:\n{process_ansible.stdout}\n{process_ansible.stderr}")
        raise Exception(f"Ansible failed: {process_ansible.stderr}")

    print(f"  [Ansible] ติดตั้งบน {ip} สำเร็จ")

    # --- ขั้นตอน B: รัน iPerf3 Client ---
    # (Worker (Container นี้) ยิง iperf3 -c ไปหาเป้าหมาย)
    iperf_cmd = ["iperf3", "-c", ip, "-J"] # -J = JSON Output
    
    print(f"  [iperf3] เริ่มทดสอบกับ {ip}...")
    process_iperf = subprocess.run(iperf_cmd, capture_output=True, text=True)

    if process_iperf.returncode != 0:
        # ถ้า iperf3 ล้มเหลว (เช่น เป้าหมายไม่ได้รัน server)
        print(f"❌ [iperf3] ล้มเหลวสำหรับ {ip}:\n{process_iperf.stderr}")
        raise Exception(f"iperf3 failed: {process_iperf.stderr}")

    print(f"  [iperf3] ทดสอบ {ip} สำเร็จ")
    
    # คืนค่าผลลัพธ์ (stdout) ซึ่งเป็น JSON String
    return process_iperf.stdout


def callback(ch, method, properties, body):
    """
    ฟังก์ชันที่จะถูกเรียกอัตโนมัติเมื่อมี "งาน" เข้ามาจาก RabbitMQ
    """
    data = {}
    try:
        # body จะมาเป็น bytes, เราต้อง decode เป็น string แล้ว parse เป็น JSON
        data = json.loads(body.decode('utf-8'))
        ip = data.get("ip")
        user = data.get("username")
        password = data.get("password")

        # ตรวจสอบว่ามีข้อมูลครบ
        if not all([ip, user, password]):
            print(f"❌ [Worker] ข้อความไม่สมบูรณ์: {body}")
            # ถ้าข้อความพัง ให้ Ack ทิ้งไปเลย (Poison Message)
            ch.basic_ack(delivery_tag=method.delivery_tag)
            return

        # --- 3. ทำงานจริง ---
        iperf_result_str = run_ansible_and_iperf(ip, user, password)
        iperf_result_json = json.loads(iperf_result_str)

        # --- 4. บันทึกผลลง MongoDB ---
        db_entry = {
            "router_ip": ip,
            "timestamp": datetime.datetime.now(datetime.timezone.utc), # ใช้เวลา UTC
            "test_data": iperf_result_json # เก็บ JSON ทั้งก้อน
        }
        mycol_results.insert_one(db_entry)
        print(f"✅ [Worker] บันทึกผลของ {ip} ลง MongoDB เรียบร้อย")

        # --- 5. ส่งสัญญาณ "เสร็จสิ้น" (เฉพาะเมื่อสำเร็จ) ---
        print(f"  [Ack] ยืนยันการทำงาน {ip} กลับไปที่ RabbitMQ")
        ch.basic_ack(delivery_tag=method.delivery_tag)

    except Exception as e:
        # --- 6. ถ้าล้มเหลว (เช่น รหัสผ่านผิด, iperf พัง) ---
        print(f"❌ [Worker] ❗❗ เกิดข้อผิดพลาดในการประมวลผล {data.get('ip')}: {e}")
        # เราจะ "Nack" (Negative Ack) และบอกให้ Requeue=False
        # เพื่อไม่ให้งานนี้กลับเข้าคิว (ป้องกันการวนลูปซ้ำๆ)
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
        print(f"  [Nack] ส่งงาน {data.get('ip')} ที่ล้มเหลวทิ้ง")
    
    print(f"--- ☕ [Worker] รองานต่อไป ---")


def start_worker():
    """
    เชื่อมต่อ RabbitMQ และเริ่มรอรับงาน
    """
    print("🚀 [Worker] เริ่มการทำงาน...")
    while True:
        try:
            connection = pika.BlockingConnection(pika.ConnectionParameters(host=RABBITMQ_HOST, heartbeat=600))
            channel = connection.channel()
            
            # สร้าง Queue (ถ้ายังไม่มี)
            # durable=True หมายความว่าคิวจะไม่หายไป แม้ RabbitMQ จะรีสตาร์ท
            channel.queue_declare(queue=QUEUE_NAME, durable=True)
            
            # บอก RabbitMQ ว่า "ส่งงานมาให้ฉันทีละ 1 ชิ้นเท่านั้น"
            channel.basic_qos(prefetch_count=1)
            
            # เริ่ม "ฟัง" คิว และผูกกับฟังก์ชัน callback
            channel.basic_consume(queue=QUEUE_NAME, on_message_callback=callback)

            print(f"✅ [Worker] เชื่อมต่อ RabbitMQ สำเร็จ กำลังรอข้อความในคิว '{QUEUE_NAME}'...")
            channel.start_consuming()
        
        except pika.exceptions.AMQPConnectionError as e:
            print(f"❌ [Worker] ไม่สามารถเชื่อมต่อ RabbitMQ: {e}. กำลังลองใหม่ใน 5 วินาที...")
            time.sleep(5)
        except KeyboardInterrupt:
            print("🛑 [Worker] กำลังปิดการทำงาน...")
            if 'connection' in locals() and connection.is_open:
                connection.close()
            break

if __name__ == "__main__":
    # ตรวจสอบว่า Environment Variables ที่จำเป็นถูกตั้งค่าแล้วหรือยัง
    if not all([MONGO_URI, DB_NAME, RABBITMQ_HOST]):
        print("❌ [Worker] Error: MONGO_URI, DB_NAME, และ RABBITMQ_HOST ต้องถูกตั้งค่า")
        sys.exit(1)
    
    start_worker()

