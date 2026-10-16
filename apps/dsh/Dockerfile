FROM node:22-bookworm

RUN npm install -g pnpm@10.34.7 @deepseek-ai/dsh@0.2.1-alpha.5

WORKDIR /opt/console-shell
COPY apps/console-plugins/shell/package.json apps/console-plugins/shell/package-lock.json apps/console-plugins/shell/build.mjs apps/console-plugins/shell/cordis.patch.yml ./
COPY apps/console-plugins/shell/src ./src
RUN npm ci && npm run build

COPY apps/dsh/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENV DSH_HOME=/var/lib/dsh \
    DSH_PUBLIC_URL=http://127.0.0.1:8080/ \
    SMP_AUTH_URL=http://web-api:8000/api/auth/me
EXPOSE 3080
ENTRYPOINT ["/entrypoint.sh"]
