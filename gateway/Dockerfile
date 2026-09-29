FROM nginx:alpine
RUN printf 'proxy_set_header Host $host;\nproxy_set_header X-Real-IP $remote_addr;\nproxy_connect_timeout 3s;\nproxy_read_timeout 10s;\n' > /etc/nginx/proxy_params.conf
COPY default.conf /etc/nginx/conf.d/default.conf
COPY static/ /usr/share/nginx/html/
