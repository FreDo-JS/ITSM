# svcdesk image. Lab 5 hardening: the base is pinned by digest (python:3.13-slim, index digest of 2026-11-14), OS
# packages are upgraded right after FROM, and pip is removed once it has installed the pins (nothing here calls pip
# at run time), so pip's vendored copies of other packages cannot trip the image gate.
# Two rules from API.md section 9: install every dependency at BUILD time (the grader's sandbox has no network once
# the image is built) and listen on port 8080 inside the container.
FROM python:3.13-slim@sha256:e48f59cdba69a3cbd9ed2cf0f348d90d45a8d350d98134cf1070bc106ee9ed90

WORKDIR /app

RUN apt-get update && apt-get upgrade -y && rm -rf /var/lib/apt/lists/*

# Dependencies first, so Docker caches this layer while you edit code.
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt && pip uninstall -y pip

# Your code lives under src/ (see src/README.md).
COPY src/ /app/src/

# The SQLite file goes to /data (a named volume in docker-compose.yml), so tickets survive a restart.
RUN mkdir -p /data
ENV SVCDESK_DB=/data/svcdesk.db

EXPOSE 8080
CMD ["uvicorn", "svcdesk.main:app", "--app-dir", "/app/src", "--host", "0.0.0.0", "--port", "8080"]
