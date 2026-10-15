FROM node:22-alpine AS build

WORKDIR /src
COPY apps/web-ui/package.json ./
COPY apps/web-ui/ ./
RUN npm install && npm run build

FROM nginx:1.27-alpine
COPY apps/web-ui/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /src/dist /usr/share/nginx/html
