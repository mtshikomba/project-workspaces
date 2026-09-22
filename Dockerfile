FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=config.settings

RUN groupadd --gid 1000 app \
    && useradd --uid 1000 --gid 1000 --create-home --shell /usr/sbin/nologin app \
    && mkdir -p /app/staticfiles /app/media \
    && chown -R app:app /app

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY --chown=app:app . .
COPY entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod 0755 /usr/local/bin/entrypoint.sh \
    && chown -R app:app /app

USER app

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD ["python", "-c", "import urllib.request; response = urllib.request.urlopen('http://127.0.0.1:8000/health/', timeout=3); raise SystemExit(0 if response.status == 200 else 1)"]

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "config.wsgi:application"]
