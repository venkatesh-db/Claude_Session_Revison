FROM nginx:1.27-alpine

COPY index.html /usr/share/nginx/html/index.html
COPY config.template.js /etc/nginx/config.template.js

ENV API_BASE=http://localhost:5000

EXPOSE 80

CMD ["/bin/sh", "-c", "envsubst '$API_BASE' < /etc/nginx/config.template.js > /usr/share/nginx/html/config.js && nginx -g 'daemon off;'"]
