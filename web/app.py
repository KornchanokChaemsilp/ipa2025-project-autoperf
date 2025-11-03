from flask import Flask, render_template, request, redirect, url_for
import pika
import json
import datetime

app = Flask(__name__)

# --- ฐานข้อมูลจำลอง (GLOBAL) ---
# เราจะใช้ลิสต์นี้เป็นข้อมูลหลัก เพื่อให้ลบและเพิ่มได้
DUMMY_RESULTS = [
    {"ip": "192.168.1.100", "status": "Completed", "bandwidth": "940 Mbits/sec"},
    {"ip": "10.0.0.5", "status": "Testing...", "bandwidth": "N/A"}
]

DUMMY_INTERFACE_DATA = {
    "192.168.1.100": [
        {"timestamp": datetime.datetime.now(), "interfaces": [
            {"interface": "GigabitEthernet1", "ip_address": "192.168.1.100", "status": "up", "proto": "up"}
        ]}
    ],
    "10.0.0.5": [
        {"timestamp": datetime.datetime.now(), "interfaces": [
            {"interface": "eth0", "ip_address": "10.0.0.5", "status": "up", "proto": "up"}
        ]}
    ]
}
# ---------------------------------

def send_job_to_rabbitmq(ip_target):
    """
    ฟังก์ชันจำลองการส่ง Job ไป RabbitMQ (ตาม Requirement)
    """
    job_data = {"target_ip": ip_target, "task": "install_iperf_server"}
    
    # (ในโค้ดจริง: จะมีโค้ด pika.BlockingConnection ... channel.basic_publish ... )
    
    print(f"[Job Sent] ส่ง Job สำหรับ IP: {ip_target} ไปยัง RabbitMQ สำเร็จ")
    

@app.route('/')
def index():
    """หน้าหลัก (List View)"""
    # ดึงข้อมูลจากฐานข้อมูลจำลอง
    return render_template('index.html', results=DUMMY_RESULTS)


@app.route('/add', methods=['POST'])
def add_target():
    """
    รับ Job (เหมือน Guestbook 'Add Comment')
    """
    if request.method == 'POST':
        # 1. ดึง IP Address ที่ผู้ใช้กรอกจากฟอร์ม
        ip_target = request.form['ip_address']
        
        # (ป้องกันการเพิ่ม IP ซ้ำ)
        if not any(d['ip'] == ip_target for d in DUMMY_RESULTS):
            
            # 2. ส่ง Job ไปให้ RabbitMQ (ตาม Requirement ของ AutoPerf)
            send_job_to_rabbitmq(ip_target)
            
            # 3. เพิ่ม IP ใหม่นี้ลงในลิสต์ (เพื่อให้แสดงผลทันที)
            # (ในระบบจริง Worker อาจจะเป็นคนอัปเดต Status นี้)
            new_target = {
                "ip": ip_target, 
                "status": "Provisioning...", # สถานะเริ่มต้น
                "bandwidth": "N/A"
            }
            DUMMY_RESULTS.append(new_target)
            
    # 4. กลับไปที่หน้าหลัก
    return redirect(url_for('index'))


@app.route('/delete', methods=['POST'])
def delete_target():
    """
    (ใหม่!) รับคำสั่งลบ (เหมือน Guestbook 'Delete')
    """
    if request.method == 'POST':
        ip_to_delete = request.form['ip_to_delete']
        
        # ลบ IP นี้ออกจากฐานข้อมูลจำลอง
        # (ใช้ List Comprehension เพื่อสร้างลิสต์ใหม่ที่ไม่มี IP นี้)
        global DUMMY_RESULTS
        DUMMY_RESULTS = [item for item in DUMMY_RESULTS if item['ip'] != ip_to_delete]
        
        print(f"ลบ IP: {ip_to_delete} ออกจากระบบแล้ว")
        
        # (ในระบบจริง อาจต้องส่ง Job "Decommission" ไป RabbitMQ ด้วย)

    return redirect(url_for('index'))


@app.route('/detail/<target_ip>')
def show_detail(target_ip):
    """หน้าแสดงรายละเอียด (Detail View)"""
    
    data = DUMMY_INTERFACE_DATA.get(target_ip, []) 
    return render_template('detail.html', 
                           router_ip=target_ip, 
                           interface_data=data)


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)