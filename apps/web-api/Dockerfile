FROM node:22-bookworm-slim AS deriver

WORKDIR /opt/wallet-deriver
COPY apps/wallet-deriver/package.json apps/wallet-deriver/package-lock.json apps/wallet-deriver/.npmrc ./
RUN npm ci --omit=dev --ignore-scripts
COPY apps/wallet-deriver/derive.mjs ./
RUN mkdir -p /opt/node/bin && cp /usr/local/bin/node /opt/node/bin/node && chmod 755 /opt/node/bin/node

FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    WALLET_DERIVER_NODE=/opt/node/bin/node \
    WALLET_DERIVER_SCRIPT=/opt/wallet-deriver/derive.mjs

WORKDIR /src/web-api

COPY --from=deriver /opt/node /opt/node
COPY --from=deriver /opt/wallet-deriver /opt/wallet-deriver
COPY packages/smpcore /src/smpcore
COPY apps/web-api /src/web-api
COPY components /components

ENV COMPONENTS_DIR=/components

RUN pip install --no-cache-dir /src/smpcore .

EXPOSE 8000

CMD ["uvicorn", "smp_web.main:app", "--host", "0.0.0.0", "--port", "8000"]
