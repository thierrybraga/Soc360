FROM nginx:1.26-alpine

LABEL maintainer="admin@example.com"
LABEL description="Nginx otimizado para segurança e desempenho"
LABEL version="1.0"

# Instala curl para healthcheck e limpa cache
RUN apk add --no-cache curl && \
    rm -f /etc/nginx/conf.d/default.conf

# Copia configurações customizadas
COPY nginx.conf /etc/nginx/nginx.conf
COPY conf.d/ /etc/nginx/conf.d/

# Garante permissões corretas para o usuário não-root
RUN chown -R nginx:nginx /etc/nginx /var/cache/nginx /var/log/nginx && \
    chmod -R 755 /etc/nginx

# Healthcheck leve e confiável
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost/health || exit 1

EXPOSE 80 443

# Executa como usuário não-privilegiado
USER nginx
CMD ["nginx", "-g", "daemon off;"]