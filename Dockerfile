FROM python:3.12-alpine AS build
WORKDIR /build
COPY requirements-web.txt .
RUN pip wheel --no-cache-dir --wheel-dir /wheels -r requirements-web.txt
RUN python -c "import urllib.request; urllib.request.urlretrieve('https://truststore.pki.rds.amazonaws.com/global/global-bundle.pem', '/rds-ca.pem')"

FROM python:3.12-alpine
RUN apk upgrade --no-cache
RUN addgroup -S -g 10001 studio && adduser -S -D -H -u 10001 -G studio studio
COPY --from=build /wheels /wheels
COPY requirements-web.txt /tmp/requirements-web.txt
RUN pip install --no-cache-dir --no-index --find-links=/wheels -r /tmp/requirements-web.txt && rm -rf /wheels /tmp/requirements-web.txt
WORKDIR /app
COPY --from=build /rds-ca.pem /app/rds-ca.pem
COPY src /app/src
RUN chown 10001:10001 /tmp && chmod 0700 /tmp
ENV PYTHONPATH=/app/src PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 LANG=C.UTF-8 LC_ALL=C.UTF-8 LANGUAGE=C
USER 10001:10001
VOLUME ["/tmp"]
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/readyz',timeout=4)"]
CMD ["python", "-m", "uvicorn", "cyberstudio.web.app:app", "--host", "0.0.0.0", "--port", "8080", "--workers", "2", "--no-access-log"]
