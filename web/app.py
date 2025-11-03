from flask import Flask, render_template, request, redirect, url_for
import pika
import json
import datetime
from pymongo import MongoClient
import os # <-- 1. Import 'os' เพื่ออ่าน Environment Variables

app = Flask(__name__)

# --- 2. ตั้งค่าการเชื่อมต่อ (อ่านจาก .env) ---
# อ่านค่าจาก Environment Variables ที่ Docker ส่งมาให้ตอน 'docker run'
DB_URL = os.environ.get("DB_URL")
DB_NAME = os.environ.get("DB_NAME")
RABBITMQ_HOST = os.environ.get("RABBITMQ_HOST")

# (ตรวจสอบว่าตั้งค่า .env มาครบ)
if not DB_URL or not DB_NAME or not RABBITMQ_HOST:
    print("!!! [Error] คุณต้องตั้งค่า DB_URL, DB_NAME, และ RABBITMQ_HOST ใน .env")
    # (ในระบบจริงควร exit หรือจัดการ error)
    # ในตัวอย่างนี้จะลองรันต่อเผื่อมีค่า default
    
try:
    # ใช้ค่าที่อ่านได้
    client = MongoClient(DB_URL)
    db = client[DB_NAME] # <-- 3. ใช้ db[DB_NAME] เพื่อใช้ตัวแปร
    results_collection = db.results # Collection สำหรับหน้าหลัก (IP, Status)
    interfaces_collection = db.interfaces # Collection สำหรับหน้า Detail (Interface)
    print(f"เชื่อมต่อ MongoDB ที่ {DB_NAME} สำเร็จ")
except Exception as e:
    print(f"!!! [Error] ไม่สามารถเชื่อมต่อ MongoDB: {e}")
# ---------------------------------

def send_job_to_rabbitmq(ip_target):
    """
    ฟังก์ชันสำหรับส่ง Job ไป RabbitMQ
    """
    job_data = {"target_ip": ip_target, "task": "install_iperf_server"}
    try:
        # 4. ใช้ค่า RABBITMQ_HOST ที่อ่านได้
        connection = pika.BlockingConnection(pika.ConnectionParameters(RABBITMQ_HOST))
        channel = connection.channel()
        channel.queue_declare(queue='ansible_job_queue', durable=True)
        
        channel.basic_publish(
            exchange='',
            routing_key='ansible_job_queue',
            body=json.dumps(job_data),
            properties=pika.BasicProperties(
                delivery_mode=2,  # ทำให้ Job ไม่หายแม้ RabbitMQ จะล่ม
            ))
        print(f"[Job Sent] ส่ง Job ไปยัง {RABBITMQ_HOST} สำเร็จ")
        connection.close()
    except Exception as e:
        print(f"!!! [Error] ไม่สามารถส่ง Job ไป RabbitMQ: {e}")

@app.route('/')
def index():
    """
    หน้าหลัก - ดึงข้อมูลจาก MongoDB
    """
    try:
        results = list(results_collection.find().sort("_id", -1))
        return render_template('index.html', results=results)
    except Exception as e:
        print(f"Error reading from results_collection: {e}")
        return render_template('index.html', results=[])


@app.route('/add', methods=['POST'])
def add_target():
    """
    รับ Job และเพิ่มข้อมูลลงใน MongoDB
    """
    if request.method == 'POST':
        try:
            ip_target = request.form['ip_address']
            
            # ตรวจสอบข้อมูลซ้ำใน MongoDB
            if not results_collection.find_one({"ip": ip_target}):
                
                # (ส่ง Job ไป RabbitMQ - เหมือนเดิม)
                send_job_to_rabbitmq(ip_target)
                
                # สร้าง Document ใหม่เพื่อ Insert
                new_target = {
                    "ip": ip_target, 
                    "status": "Provisioning...",
                    "bandwidth": "N/A",
                    "last_updated": datetime.datetime.now()
                }
                # Insert ลง MongoDB
                results_collection.insert_one(new_target)
        except Exception as e:
            print(f"Error in add_target: {e}")
            
    return redirect(url_for('index'))


@app.route('/delete', methods=['POST'])
def delete_target():
    """
    ลบข้อมูลออกจาก MongoDB
    """
    if request.method == 'POST':
        try:
            ip_to_delete = request.form['ip_to_delete']
            
            # ลบ Document ที่ตรงเงื่อนไขออกจาก MongoDB
            results_collection.delete_one({"ip": ip_to_delete})
            
            # (ถ้าต้องการลบข้อมูล Detail ด้วย)
            # interfaces_collection.delete_many({"router_ip": ip_to_delete})
        except Exception as e:
            print(f"Error in delete_target: {e}")
            
    return redirect(url_for('index'))


@app.route('/detail/<target_ip>')
def show_detail(target_ip):
    """
    หน้าแสดงรายละเอียด - ดึงข้อมูล Interface จาก MongoDB
    """
    try:
        # (ข้อมูลนี้จะถูกเพิ่มโดย Worker อื่น ไม่ใช่จากหน้าเว็บ)
        data = list(interfaces_collection.find({"router_ip": target_ip}))
        
        return render_template('detail.html', 
                               router_ip=target_ip, 
                               interface_data=data)
    except Exception as e:
        print(f"Error in show_detail: {e}")
        return render_template('detail.html', 
                               router_ip=target_ip, 
                               interface_data=[])

if __name__ == '__main__':
    # 5. ทำให้ตรงกับ Dockerfile (EXPOSE 8080)
    app.run(debug=True, host='0.0.0.0', port=8080)
