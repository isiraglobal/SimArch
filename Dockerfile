FROM python:3.13-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    SIMARCH_HOME=/app/data \
    SIMARCH_DASHBOARD_HOST=0.0.0.0 \
    SIMARCH_DASHBOARD_PORT=8400

# Install dependencies and package
COPY pyproject.toml README.md ./
COPY src/ ./src/
COPY examples/ ./examples/

RUN pip install --no-cache-dir .

# Create volume for persistent SQLite database and artifacts
VOLUME ["/app/data"]

EXPOSE 8400

ENTRYPOINT ["simarch"]
CMD ["serve", "--host", "0.0.0.0", "--port", "8400"]
