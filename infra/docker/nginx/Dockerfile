FROM nginx:1.25-alpine

LABEL maintainer="Open-Monitor Team" \
      version="3.0.0" \
      description="NGINX Reverse Proxy for Open-Monitor"

# Install additional tools
RUN apk add --no-cache curl

# Remove default nginx configuration
RUN rm -rf /etc/nginx/conf.d/default.conf

# Copy configuration files
COPY nginx.conf /etc/nginx/nginx.conf
COPY conf.d/ /etc/nginx/conf.d/

# Create directories for SSL and HTML
RUN mkdir -p /etc/nginx/ssl /usr/share/nginx/html /var/www/certbot

# Copy default HTML files
COPY html/ /usr/share/nginx/html/

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8080/nginx-health || exit 1

# Expose ports
EXPOSE 8080 8443

# Run nginx
CMD ["nginx", "-g", "daemon off;"]