# WineLib in one container: the API serves the built web app. Everything you add (the database, photos, map
# outlines, backups, plug-ins) lives in /data: keep it on a volume (docker-compose.yml).
#
#   docker compose up -d            # the published image (ghcr.io/maxlmn/winelib)
#   docker compose up -d --build    # or built from this checkout

# The web app, built to static files
FROM node:22-slim AS web
WORKDIR /web
COPY app/web/package.json app/web/package-lock.json ./
RUN npm ci
COPY app/web/ ./
RUN npm run build

# The API, serving /api and the web app
FROM python:3.11-slim
WORKDIR /app
COPY app/api/requirements.txt app/api/requirements.txt
RUN pip install --no-cache-dir -r app/api/requirements.txt
COPY app/api/ app/api/
COPY --from=web /web/build app/web/build

# Not root: a user of its own, owning the data folder
RUN useradd --create-home --uid 1000 winelib && mkdir /data && chown winelib /data
USER winelib
ENV WINELIB_DATA=/data PYTHONUNBUFFERED=1
VOLUME /data

WORKDIR /app/app/api
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=4)"
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
