# ── Stage 1: builder ────────────────────────────────────────────────
# Install Python dependencies and Playwright Chromium browser.
FROM python:3.11-slim AS builder

WORKDIR /app

ENV PYTHONUTF8=1 \
    PYTHONIOENCODING=utf-8

# System deps needed to build wheels and install Playwright browsers
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy project metadata + source so pip can resolve & install
COPY pyproject.toml ./
COPY run_all.py config.py tg_formatter.py logger_setup.py main.py ./
# If any of the above are missing, COPY won't fail the build if we use a glob
# but keep explicit for clarity.

# Install the project (and its dependencies) into /install
RUN pip install --no-cache-dir --prefix=/install .

# Install Playwright Chromium into the builder stage
RUN playwright install chromium \
    && playwright install-deps chromium

# ── Stage 2: production ─────────────────────────────────────────────
# Chrome CDP is provided externally via docker-compose, so we do NOT
# install Playwright browsers here — only the Python packages.
FROM python:3.11-slim

WORKDIR /app

ENV PYTHONUTF8=1 \
    PYTHONIOENCODING=utf-8

# Copy installed Python packages from builder
COPY --from=builder /install /usr/local

# Copy application source code
COPY run_all.py config.py tg_formatter.py logger_setup.py main.py ./

# Copy any data/config files that might exist (best-effort)
COPY .env* ./

CMD ["python", "run_all.py"]