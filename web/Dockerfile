FROM python:3.12-slim
WORKDIR /app
COPY . /app
RUN pip install -r requirements.txt
EXPOSE 8080

# บังคับให้ Python ส่ง output (stdout/stderr) ออกมาทันทีโดยไม่บัฟเฟอร์
# ซึ่งจำเป็นมากเพื่อให้ 'docker logs' ทำงานได้ถูกต้อง
ENV PYTHONUNBUFFERED=1

CMD ["python3", "app.py"]
