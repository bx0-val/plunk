FROM python:3.12-slim
WORKDIR /app
COPY server/requirements.lock /app/server/requirements.lock
RUN pip install --no-cache-dir -r /app/server/requirements.lock && useradd -u 10001 -m plunk && mkdir /state /uploads && chown plunk:plunk /state /uploads
COPY server /app/server
USER 10001:10001
ENV PLUNK_CONFIG=/app/config.json PYTHONDONTWRITEBYTECODE=1
EXPOSE 8000
CMD ["uvicorn", "server.app:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000", "--no-access-log", "--limit-concurrency", "16"]
