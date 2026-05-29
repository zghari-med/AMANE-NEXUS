# ═══════════════════════════════════════════════════════════════════════════
# Dockerfile multi-stage — PFE MSID-TAM Surveillance Platform
# Stage 1 : backend-builder  (Python dependencies)
# Stage 2 : frontend-builder (Node.js build)
# Stage 3 : runtime          (Python 3.10-slim + Nginx)
# ═══════════════════════════════════════════════════════════════════════════

# ── Stage 1 : backend-builder ───────────────────────────────────────────────
FROM python:3.10-slim AS backend-builder

WORKDIR /build/backend

# Installer les dépendances système nécessaires
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ libgl1 libglib2.0-0 libsm6 libxrender1 libxext6 \
    && rm -rf /var/lib/apt/lists/*

# Copier et installer les dépendances Python
COPY backend/requirements.txt .
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt --target /build/python-packages

# Copier le code backend
COPY backend/ .


# ── Stage 2 : frontend-builder ──────────────────────────────────────────────
FROM node:18-alpine AS frontend-builder

WORKDIR /build/frontend

# Copier package.json et installer les dépendances
COPY frontend/package*.json ./
RUN npm ci --silent

# Copier le code source et builder
COPY frontend/ .
RUN npm run build


# ── Stage 3 : runtime ───────────────────────────────────────────────────────
FROM python:3.10-slim AS runtime

LABEL maintainer="Amane — PFE MSID-TAM 2026"
LABEL description="Système de Surveillance Intelligente Multi-Agent"

# Installer Nginx + dépendances système
RUN apt-get update && apt-get install -y --no-install-recommends \
    nginx supervisor libgl1 libglib2.0-0 libsm6 libxrender1 libxext6 \
    && rm -rf /var/lib/apt/lists/*

# Créer l'utilisateur non-root
RUN useradd -m -u 1000 surveillance

# ── Backend ─────────────────────────────────────────────────────────────────
WORKDIR /app/backend

# Copier les packages Python installés
COPY --from=backend-builder /build/python-packages /usr/local/lib/python3.10/site-packages/
COPY --from=backend-builder /build/backend /app/backend/

# Dossiers runtime
RUN mkdir -p /app/backend/uploads /app/backend/captures /app/backend/exports /app/backend/data \
    && chown -R surveillance:surveillance /app/backend/

# ── Frontend (via Nginx) ─────────────────────────────────────────────────────
COPY --from=frontend-builder /build/frontend/dist /usr/share/nginx/html/
COPY nginx.conf /etc/nginx/nginx.conf

# ── Supervisor (gère Nginx + Flask) ─────────────────────────────────────────
COPY docker/supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# ── Variables d'environnement ────────────────────────────────────────────────
ENV MONGO_URI=mongodb://mongodb:27017/ \
    REDIS_HOST=redis \
    SECRET_KEY=pfe_surveillance_2026_docker \
    ANALYTICS_CACHE_TTL=3600 \
    BENCHMARK_FILE_PATH=/app/backend/data/benchmark_results.json \
    PYTHONPATH=/app/backend \
    PYTHONUNBUFFERED=1

# Ports exposés
EXPOSE 80 5000

# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:5000/api/health || exit 1

# Démarrage via supervisor
CMD ["/usr/bin/supervisord", "-n", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
