from flask import Flask, render_template, request, redirect, url_for

# import pika  <- ลบออก
# import json  <- ลบออก
import datetime
from pymongo import MongoClient
import os

app = Flask(__name__)

# --- 1. อ่านค่า Config (ลบส่วน RabbitMQ) ---
MONGO_URI = os.environ.get("MONGO_URI")
DB_NAME = os.environ.get("DB_NAME")
# --- ลบตัวแปร RABBITMQ_ ทั้งหมด ---

# ⬇️ [แก้ไข] ปรับการตรวจสอบ ENV
if not all([MONGO_URI, DB_NAME]):
    print("!!! [Error] ไม่พบ Environment Variables \
           ที่จำเป็น (MONGO_URI, DB_NAME)")

try:
    client = MongoClient(MONGO_URI)
    db = client[DB_NAME]

    # Collection ที่เก็บ "เป้าหมาย" (IP, user, pass)
    targets_collection = db.targets

    # Collection ที่เก็บ "ผลลัพธ์ iperf" (ที่ Worker ส่งมา)
    iperf_results_collection = db.iperf3_results

    print(f"เชื่อมต่อ MongoDB ที่ {DB_NAME} สำเร็จ")
except Exception as e:
    print(f"!!! [Error] ไม่สามารถเชื่อมต่อ MongoDB: {e}")
# ---------------------------------


# ⬇️ [แก้ไข] ลบฟังก์ชัน send_job_to_rabbitmq() ทั้งหมด
# ... (ส่วนของ pika ถูกลบออก) ...


@app.route("/")
def index():
    """
    หน้าหลัก แสดง Target ทั้งหมด
    """
    try:
        results = list(targets_collection.find().sort("ip", 1))

        # (ส่วนนี้คือการคำนวณ Status/Bandwidth ล่าสุด)
        for r in results:
            last_iperf = iperf_results_collection.find_one(
                {"router_ip": r["ip"]}, sort=[("timestamp", -1)]
            )
            if last_iperf and "test_data" in last_iperf:
                r["status"] = "Finished"

                # ดึงค่า bits_per_second ออกมาใส่ตัวแปรง่ายต่อการอ่านและดีบัก
                # ใช้ .get() ซ้อนกันอย่างปลอดภัย พร้อมค่า default
                bits_per_second = (
                    last_iperf.get("test_data", {})
                    .get("end", {})
                    .get("sum_received", {})
                    .get("bits_per_second", 0)
                )

                # คำนวณและจัดรูปแบบ f-string ในบรรทัดที่ชัดเจน
                bandwidth_mbps = bits_per_second / 1_000_000  # 1e6
                r["bandwidth"] = f"{bandwidth_mbps:.2f} Mbps"

            # ⬇️ [แก้ไข] เปลี่ยนการแสดงสถานะเล็กน้อย
            elif r.get("status") == "Waiting for Scheduler":
                r["status"] = "Waiting..."
                r["bandwidth"] = "N/A"
            elif not r.get("status"):
                r["status"] = "N/A"
                r["bandwidth"] = "N/A"

        return render_template("index.html", results=results)
    except Exception as e:
        print(f"Error reading from targets_collection: {e}")
        return render_template("index.html", results=[])


# ⬇️ [แก้ไข] Route นี้จะ "ไม่ส่ง" คิวแล้ว
@app.route("/add", methods=["POST"])
def add_target():
    """
    เพิ่ม/อัปเดต Target ลงใน Database เพื่อให้ Scheduler นำไปทำงาน
    """
    if request.method == "POST":
        try:
            # 1. รับค่า 3 ค่าจากฟอร์ม
            ip_target = request.form["ip_address"]
            username = request.form["username"]
            password = request.form["password"]  # (Scheduler จะใช้ข้อมูลนี้)

            # 2. บันทึก/อัปเดต Target ลง DB (เพื่อให้ Scheduler ใช้ได้)
            target_data = {
                "ip": ip_target,
                "username": username,
                "password": password,
                "status": "Waiting for Scheduler",  # ⬅️ [แก้ไข] สถานะใหม่
                "last_updated": datetime.datetime.now(datetime.timezone.utc),
            }
            targets_collection.update_one(
                {"ip": ip_target},
                {"$set": target_data},
                upsert=True,  # ถ้าไม่มี IP นี้ ให้สร้างใหม่ (Insert)
            )

            # 3. ⬇️ [แก้ไข] ลบการส่ง Job ออก
            # send_job_to_rabbitmq(ip_target, username, password) <- ลบออก

        except Exception as e:
            print(f"Error in add_target: {e}")
    return redirect(url_for("index"))


@app.route("/delete", methods=["POST"])
def delete_target():
    """
    ลบ Target (และผลการทดสอบทั้งหมด)
    """
    if request.method == "POST":
        try:
            ip_to_delete = request.form["ip_to_delete"]
            # 1. ลบ Target
            targets_collection.delete_one({"ip": ip_to_delete})
            # 2. (แนะนำ) ลบผลทดสอบเก่าๆ ของ IP นี้ด้วย
            iperf_results_collection.delete_many({"router_ip": ip_to_delete})
        except Exception as e:
            print(f"Error in delete_target: {e}")
    return redirect(url_for("index"))


@app.route("/detail/<target_ip>")
def show_detail(target_ip):
    """
    แสดงรายละเอียดผลการทดสอบย้อนหลังของ IP นั้นๆ
    """
    try:
        iperf_history = list(
            iperf_results_collection.find({"router_ip": target_ip})
                                    .sort("timestamp", -1)
        )  # เรียงจากใหม่ไปเก่า

        return render_template(
            "detail.html", router_ip=target_ip, iperf_history=iperf_history
        )
    except Exception as e:
        print(f"Error in show_detail: {e}")
        return render_template("detail.html",
                            router_ip=target_ip,
                            iperf_history=[])


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=8080)
