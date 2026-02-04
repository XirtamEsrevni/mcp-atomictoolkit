FROM python:3.13-slim

WORKDIR /app
COPY . .

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

EXPOSE 7860
ENV HOST=0.0.0.0
ENV PORT=7860

CMD ["python", "hf_server.py"]
