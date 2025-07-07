# Dockerfile
FROM python:3.12-slim

# 1) Ustaw katalog roboczy
WORKDIR /app

# 2) Skopiuj plik z zależnościami i zainstaluj je
COPY requirements.txt .
RUN apt-get update \
 && apt-get install -y --no-install-recommends gcc \
 && pip install --no-cache-dir -r requirements.txt \
 && apt-get purge -y --auto-remove gcc \
 && rm -rf /var/lib/apt/lists/*

# 3) Skopiuj resztę kodu aplikacji
COPY . .

# 4) Ustaw backend Matplotlib na Agg (non-GUI)
ENV MPLBACKEND=Agg

# 5) Wystaw port, na którym Flask będzie nasłuchiwać
EXPOSE 5000

# 6) Domyślne polecenie uruchomienia – gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app:app", "--workers", "2"]
