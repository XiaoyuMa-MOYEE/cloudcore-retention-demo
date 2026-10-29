FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 CLOUDCORE_RUNTIME_DIR=/var/data/web_runtime
WORKDIR /app
COPY requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY src ./src
COPY backend ./backend
COPY config.yaml ./config.yaml
COPY data/input/模拟数据.csv ./data/input/模拟数据.csv
EXPOSE 8000
CMD ["uvicorn", "backend.app:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers"]
