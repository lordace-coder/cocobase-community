# ── Stage 1: Build the SvelteKit dashboard ──────────────────────────────────
FROM node:22-alpine AS dashboard-builder

WORKDIR /dashboard

# Install deps first (layer cache)
COPY dashboard/package*.json ./
RUN npm ci

# Copy source and build
COPY dashboard/ ./
RUN npm run build

# ── Stage 2: Python API ──────────────────────────────────────────────────────
FROM python:3.13-slim

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source
COPY . .

# Copy built dashboard from stage 1
COPY --from=dashboard-builder /dashboard/build ./dashboard/build

EXPOSE 9000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "9000"]
