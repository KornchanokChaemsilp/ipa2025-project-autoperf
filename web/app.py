from flask import Flask, render_template, request, redirect, url_for
import pika
import json
import datetime
from pymongo import MongoClient
import os 

app = Flask(__name__)

# --- 1. อ่านค่า Config ใหม่ (ตามที่ docker-compose ส่งมา) ---
# อ่าน MONGO_URI และ DB_NAME (ipa2025_db)
MONGO_URI = os.environ.get("MONGO_URI") 
DB_NAME = os.environ.get("DB_NAME")
# อ่าน RABBITMQ_HOST (จาก .env)
RABBITMQ_HOST = os.environ.get("RABBITMQ_HOST")

if not MONGO_URI or not DB_NAME or not RABBITMQ_HOST:
    print("!!! [Error] ไม่พบ Environment Variables ที่จำเป็น (MONGO_URI, DB_NAME, RABBITMQ_HOST)")

try:
    # --- 2. ใช้ MONGO_URI ในการเชื่อมต่อ ---
    client = MongoClient(MONGO_URI)
    # --- 3. ใช้ DB_NAME (ipa2025_db) ---
    db = client[DB_NAME] 
    results_collection = db.results 
    interfaces_collection = db.interfaces
    iperf_results_collection = db.iperf_results # (เพิ่มอันนี้ด้วย)
    
    print(f"เชื่อมต่อ MongoDB ที่ {DB_NAME} สำเร็จ")
except Exception as e:
    print(f"!!! [Error] ไม่สามารถเชื่อมต่อ MongoDB: {e}")
# ---------------------------------

# (โค้ดส่วนที่เหลือของ app.py ไม่ต้องแก้ไข)
# ... (ฟังก์ชัน send_job_to_rabbitmq(ip_target) ... )
def send_job_to_rabbitmq(ip_target):
    job_data = {"target_ip": ip_target, "task": "install_iperf_server"}
    try:
        connection = pika.BlockingConnection(pika.ConnectionParameters(RABBITMQ_HOST))
        channel = connection.channel()
        channel.queue_declare(queue='ansible_job_queue', durable=True)
        channel.basic_publish(
            exchange='',
            routing_key='ansible_job_queue',
            body=json.dumps(job_data),
            properties=pika.BasicProperties(delivery_mode=2))
        print(f"[Job Sent] ส่ง Job ไปยัง {RABBITMQ_HOST} สำเร็จ")
        connection.close()
    except Exception as e:
        print(f"!!! [Error] ไม่สามารถส่ง Job ไป RabbitMQ: {e}")

# ... (โค้ด @app.route('/') ... )
@app.route('/')
def index():
    try:
        results = list(results_collection.find().sort("_id", -1))
        return render_template('index.html', results=results)
    except Exception as e:
        print(f"Error reading from results_collection: {e}")
        return render_template('index.html', results=[])

# ... (โค้ด @app.route('/add', ...) ... )
@app.route('/add', methods=['POST'])
def add_target():
    if request.method == 'POST':
        try:
            ip_target = request.form['ip_address']
            if not results_collection.find_one({"ip": ip_target}):
                send_job_to_rabbitmq(ip_target)
                new_target = {
                    "ip": ip_target, 
                    "status": "Provisioning...",
                    "bandwidth": "N/A",
                    "last_updated": datetime.datetime.now()
                }
                results_collection.insert_one(new_target)
        except Exception as e:
            print(f"Error in add_target: {e}")
    return redirect(url_for('index'))

# ... (โค้ด @app.route('/delete', ...) ... )
@app.route('/delete', methods=['POST'])
def delete_target():
    if request.method == 'POST':
        try:
            ip_to_delete = request.form['ip_to_delete']
            results_collection.delete_one({"ip": ip_to_delete})
        except Exception as e:
            print(f"Error in delete_target: {e}")
    return redirect(url_for('index'))

# ... (โค้ด @app.route('/detail/<target_ip>') ... )
@app.route('/detail/<target_ip>')
def show_detail(target_ip):
    try:
        interface_data = list(interfaces_collection.find({"router_ip": target_ip}))
        iperf_history = list(iperf_results_collection.find(
            {"ip": target_ip}
        ).sort("timestamp", -1))

        return render_template('detail.html', 
                               router_ip=target_ip, 
                               interface_data=interface_data,
                               iperf_history=iperf_history)
    except Exception as e:
        print(f"Error in show_detail: {e}")
        return render_template('detail.html', 
                               router_ip=target_ip, 
                               interface_data=[],
                               iperf_history=[])

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8080)

