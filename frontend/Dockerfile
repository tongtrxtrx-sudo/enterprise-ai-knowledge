FROM node:20-alpine AS builder

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .
RUN npm run build

FROM python:3.12-alpine

WORKDIR /app

COPY scripts /app/scripts
COPY --from=builder /app/dist /app/dist

CMD ["sh", "-c", "python /app/scripts/validate_env.py frontend && python -m http.server ${FRONTEND_PORT:-5173} --bind 0.0.0.0 --directory /app/dist"]
