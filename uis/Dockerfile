FROM node:22-alpine

WORKDIR /app/uis

COPY website/package*.json ./website/
RUN npm install --prefix ./website

COPY backoffice/package*.json ./backoffice/
RUN npm install --prefix ./backoffice

COPY . .
RUN chmod +x ./start.sh \
	&& mkdir -p ./website/node_modules ./backoffice/node_modules \
	&& chown -R node:node ./website/node_modules ./backoffice/node_modules

EXPOSE 3000 3001
USER node
CMD ["/app/uis/start.sh"]