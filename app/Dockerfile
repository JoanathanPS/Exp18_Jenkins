# ---- Stage 1: build/install deps in an isolated layer ----
FROM python:3.12-slim AS builder

WORKDIR /build
COPY requirements.txt .
# --user installs to /root/.local so we can copy just that into the final image
RUN pip install --no-cache-dir --user -r requirements.txt

# ---- Stage 2: slim runtime image ----
FROM python:3.12-slim

# Run as a non-root user (basic container security hygiene)
RUN useradd --create-home --uid 1000 appuser
WORKDIR /app

# Bring in only the installed packages from the builder stage
COPY --from=builder /root/.local /home/appuser/.local
COPY . .

# Build-time arg -> baked-in env var, so /  reports which image/commit is running
ARG APP_VERSION=dev
ENV APP_VERSION=${APP_VERSION} \
    PATH=/home/appuser/.local/bin:$PATH \
    PYTHONUNBUFFERED=1

RUN chown -R appuser:appuser /app
USER appuser

EXPOSE 5000

HEALTHCHECK --interval=30s --timeout=3s CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:5000/health')" || exit 1

# Use gunicorn in real deployments; keeping flask's built-in server here to
# stay dependency-light for a lab exercise. Swap the CMD below if you want
# production-grade serving (see README "Going further").
CMD ["python", "app.py"]
