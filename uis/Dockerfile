FROM node:22-alpine

WORKDIR /app/uis

COPY website/package*.json ./website/
RUN npm install --prefix ./website

COPY backoffice/package*.json ./backoffice/
RUN npm install --prefix ./backoffice

COPY . .
RUN chmod +x ./start.sh

EXPOSE 3000 3001
CMD ["/app/uis/start.sh"]