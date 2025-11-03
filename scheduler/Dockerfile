# 1. ใช้ Python 3.12 (เหมือน web)
FROM python:3.12-slim

# 2. ตั้งค่าโฟลเดอร์ทำงาน
WORKDIR /app

# 3. Copy 'requirements.txt' ก่อน (เพื่อใช้ Cache)
COPY requirements.txt .

# 4. ติดตั้ง Library
RUN pip install -r requirements.txt

# 5. Copy โค้ดที่เหลือทั้งหมด
COPY . .

# 6. คำสั่งเมื่อ Container เริ่มทำงาน (ให้รัน scheduler.py)
CMD ["python", "scheduler.py"]
