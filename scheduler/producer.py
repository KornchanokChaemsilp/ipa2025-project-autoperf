import pika
import json
import config  # ⬅️ Import config ของ scheduler


def send_job_to_queue(job_data, queue_name):
    """
    ส่ง Job ไปยัง RabbitMQ โดยใช้ Credentials ที่ถูกต้อง
    """
    try:
        # 1. สร้าง Credentials
        credentials = pika.PlainCredentials(config.RABBITMQ_USER,
         config.RABBITMQ_PASS)

        # 2. เชื่อมต่อโดยใช้ Credentials
        connection = pika.BlockingConnection(
            pika.ConnectionParameters(
                host=config.RABBITMQ_HOST, credentials=credentials
            )
        )

        channel = connection.channel()

        # 3. สร้างคิว (ถ้ายังไม่มี)
        # (ใช้ชื่อคิวที่ถูกต้องจาก .env)
        channel.queue_declare(queue=queue_name, durable=True)

        # 4. ส่ง Job
        channel.basic_publish(
            exchange="",
            routing_key=queue_name,
            body=json.dumps(job_data),
            properties=pika.BasicProperties(
                delivery_mode=2,  # ทำให้ Job ไม่หาย
            ),
        )

        print(
            f"  [Scheduler] ส่ง Job ของ \
                {job_data.get('ip')} ไปยังคิว '{queue_name}' สำเร็จ"
        )
        connection.close()

    except Exception as e:
        print(f"!!! [Scheduler Error] ไม่สามารถส่ง Job ไป RabbitMQ: {e}")
