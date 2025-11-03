# --- 1. เลือกอิมเมจพื้นฐาน (Base Image) ---
FROM python

# --- 2. ติดตั้ง System Dependencies ---
# Worker ของเราต้องใช้ iperf3 (สำหรับทดสอบ)
# และ sshpass (สำหรับ Ansible ที่ใช้รหัสผ่าน)
RUN apt-get update && apt-get install -y --no-install-recommends \
    iperf3 \
    sshpass \
    && rm -rf /var/lib/apt/lists/*

# --- 3. ตั้งค่า Working Directory ---
# สร้างโฟลเดอร์ /app ภายในอิมเมจ และย้ายเข้าไป
WORKDIR /app

# --- 4. ติดตั้ง Python Dependencies ---
# คัดลอก "เฉพาะ" ไฟล์ requirements.txt เข้าไปก่อน
# นี่คือเทคนิค "Layer Caching"
# ถ้าไฟล์นี้ไม่เปลี่ยน Docker จะข้ามขั้นตอนนี้ในการ build ครั้งถัดไป
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# --- 5. คัดลอกโค้ดโปรเจกต์ ---
COPY . .

# --- 6. (อัปเดต) ตั้งค่า Environment Variable สำหรับ Python ---
# บังคับให้ Python ส่ง output (stdout/stderr) ออกมาทันทีโดยไม่บัฟเฟอร์
# ซึ่งจำเป็นมากเพื่อให้ 'docker logs' ทำงานได้ถูกต้อง
ENV PYTHONUNBUFFERED=1

# --- 7. คำสั่งที่จะรันเมื่อ Container เริ่มทำงาน ---
CMD ["python", "worker.py"]