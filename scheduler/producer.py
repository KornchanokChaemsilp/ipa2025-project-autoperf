import os
import pika
import json

# อ่านค่า Config ที่ส่งมาจาก docker-compose
RABBITMQ_HOST = os.environ.get("RABBITMQ_HOST")

if not RABBITMQ_HOST:
    print("!!! [Error] ไม่พบ RABBITMQ_HOST")
    # (ควรจะ exit)

def send_job_to_queue(job_data, queue_name):
    """
    ส่ง Job (ที่เป็น dict) ไปยัง Queue ที่กำหนด
    """
    try:
        connection = pika.BlockingConnection(pika.ConnectionParameters(RABBITMQ_HOST))
        channel = connection.channel()
        
        # สร้าง Queue (ถ้ายังไม่มี)
        # **หมายเหตุ**: นี่คือ Queue ใหม่สำหรับ iPerf Worker (ไม่ใช่ ansible_job_queue)
        channel.queue_declare(queue=queue_name, durable=True)
        
        # ส่ง Job
        channel.basic_publish(
            exchange='',
            routing_key=queue_name,
            body=json.dumps(job_data), # แปลง dict เป็น JSON string
            properties=pika.BasicProperties(
                delivery_mode=2,  # ทำให้ Job ไม่หาย
            ))
        
        print(f"(Scheduler-MQ) ส่ง Job: {job_data['ip']} ไปยัง Queue: {queue_name} สำเร็จ")
        connection.close()
        
    except Exception as e:
        print(f"!!! [Error] (Scheduler-MQ) ไม่สามารถส่ง Job: {e}")
