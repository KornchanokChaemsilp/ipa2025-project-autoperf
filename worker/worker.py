# worker.py
import pika
import time

# Import โมดูลที่เราสร้างขึ้น
import config
from callback import callback  # <-- Import callback ที่แยกออกไป


def start_worker():
    """
    เชื่อมต่อ RabbitMQ และเริ่มรอรับงาน
    """
    print("🚀 [Worker] เริ่มการทำงาน...")
    while True:
        try:
            credentials = pika.PlainCredentials(
                config.RABBITMQ_USER, config.RABBITMQ_PASS
            )

            connection = pika.BlockingConnection(
                pika.ConnectionParameters(
                    host=config.RABBITMQ_HOST,
                    heartbeat=600,
                    credentials=credentials,  # ⬅️ เพิ่มบรรทัดนี้!
                )
            )

            channel = connection.channel()

            channel.queue_declare(queue=config.QUEUE_NAME, durable=True)
            channel.basic_qos(prefetch_count=1)

            # ผูกกับฟังก์ชัน callback ที่เรา import เข้ามา
            channel.basic_consume(queue=config.QUEUE_NAME,
                 on_message_callback=callback)

            print(
                f"✅ [Worker] เชื่อมต่อ RabbitMQ สำเร็จ \
                    กำลังรอข้อความในคิว '{config.QUEUE_NAME}'..."
            )
            channel.start_consuming()

        except pika.exceptions.AMQPConnectionError as e:
            print(
                f"❌ [Worker] ไม่สามารถเชื่อมต่อ RabbitMQ: \
                  {e}. กำลังลองใหม่ใน 5 วินาที..."
            )
            time.sleep(5)
        except KeyboardInterrupt:
            print("🛑 [Worker] กำลังปิดการทำงาน...")
            if "connection" in locals() and connection.is_open:
                connection.close()
            break


if __name__ == "__main__":
    # ตรวจสอบ Config ก่อนเริ่มทำงาน
    config.validate_config()

    # เริ่ม Worker
    start_worker()
