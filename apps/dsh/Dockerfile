FROM node:22-bookworm

RUN npm install -g pnpm@10.34.7 @deepseek-ai/dsh@0.2.1-alpha.5

WORKDIR /opt/console-plugins
COPY apps/console-plugins/shared ./shared
COPY apps/console-plugins/shell/package.json apps/console-plugins/shell/package-lock.json apps/console-plugins/shell/build.mjs apps/console-plugins/shell/cordis.patch.yml ./shell/
COPY apps/console-plugins/shell/src ./shell/src
COPY apps/console-plugins/dashboard/package.json apps/console-plugins/dashboard/package-lock.json apps/console-plugins/dashboard/build.mjs apps/console-plugins/dashboard/cordis.patch.yml ./dashboard/
COPY apps/console-plugins/dashboard/src ./dashboard/src
COPY apps/console-plugins/quant/package.json apps/console-plugins/quant/package-lock.json apps/console-plugins/quant/build.mjs apps/console-plugins/quant/cordis.patch.yml ./quant/
COPY apps/console-plugins/quant/src ./quant/src
COPY apps/console-plugins/accounts/package.json apps/console-plugins/accounts/package-lock.json apps/console-plugins/accounts/build.mjs apps/console-plugins/accounts/cordis.patch.yml ./accounts/
COPY apps/console-plugins/accounts/src ./accounts/src
COPY apps/console-plugins/servers/package.json apps/console-plugins/servers/package-lock.json apps/console-plugins/servers/build.mjs apps/console-plugins/servers/cordis.patch.yml ./servers/
COPY apps/console-plugins/servers/src ./servers/src
COPY apps/console-plugins/settings/package.json apps/console-plugins/settings/package-lock.json apps/console-plugins/settings/build.mjs apps/console-plugins/settings/cordis.patch.yml ./settings/
COPY apps/console-plugins/settings/src ./settings/src
RUN for name in shell dashboard quant accounts servers settings; do \
      cd /opt/console-plugins/$name && npm ci && npm run build; \
    done

COPY apps/dsh/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENV DSH_HOME=/var/lib/dsh \
    DSH_PUBLIC_URL=http://127.0.0.1:8080/ \
    SMP_AUTH_URL=http://web-api:8000/api/auth/me
EXPOSE 3080
ENTRYPOINT ["/entrypoint.sh"]
