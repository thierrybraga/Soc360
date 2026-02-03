# Open-Monitor v3.0 - Location Configurations
# Routing rules for the application

# =============================================================================
# Security Settings
# =============================================================================

# Block access to hidden files
location ~ /\. {
    deny all;
    access_log off;
    log_not_found off;
}

# Block Vite development requests
location ~* ^/(@vite|dev-sw\.js|__vite_ping) {
    return 404;
    access_log off;
    log_not_found off;
}

# Block access to backup files
location ~ ~$ {
    deny all;
    access_log off;
    log_not_found off;
}

# =============================================================================
# Static Files
# =============================================================================

# Static assets with caching
location /static/ {
    alias /app/app/static/;
    expires 30d;
    add_header Cache-Control "public, immutable";
    add_header X-Content-Type-Options "nosniff";
    
    # Gzip static files
    gzip_static on;
    
    # Allow CORS for fonts
    location ~* \.(eot|ttf|woff|woff2)$ {
        add_header Access-Control-Allow-Origin *;
        expires 30d;
    }
}

# Uploaded files
location /uploads/ {
    alias /app/uploads/;
    expires 1d;
    add_header Cache-Control "private";
    add_header X-Content-Type-Options "nosniff";
    
    # Prevent script execution
    location ~* \.(php|py|pl|sh|cgi)$ {
        deny all;
    }
}

# Report downloads - DISABLED: Let Flask handle permissions and serving
# location /reports/ {
#    alias /app/reports/;
#    expires 1h;
#    add_header Cache-Control "private";
#    add_header X-Content-Type-Options "nosniff";
#    add_header Content-Disposition "attachment";
#    
#    # Only allow PDF and specific file types
#    location ~* \.(?!pdf|xlsx|csv|json).*$ {
#        deny all;
#    }
# }

# Favicon
location = /favicon.ico {
    alias /app/app/static/images/favicon.ico;
    access_log off;
    log_not_found off;
    expires 30d;
}

# Robots.txt
location = /robots.txt {
    alias /app/app/static/robots.txt;
    access_log off;
    log_not_found off;
}

# =============================================================================
# Health Check Endpoints
# =============================================================================

location = /health {
    proxy_pass http://openmonitor_app;
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_connect_timeout 5s;
    proxy_read_timeout 5s;
    access_log off;
}

location = /ready {
    proxy_pass http://openmonitor_app;
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_connect_timeout 5s;
    proxy_read_timeout 5s;
    access_log off;
}

# =============================================================================
# Authentication Endpoints (rate limited)
# =============================================================================

location /auth/login {
    limit_req zone=login burst=5 nodelay;
    limit_conn conn_limit 10;
    
    proxy_pass http://openmonitor_app;
    include /etc/nginx/conf.d/proxy_params.inc;
}

location /auth/register {
    limit_req zone=login burst=3 nodelay;
    limit_conn conn_limit 5;
    
    proxy_pass http://openmonitor_app;
    include /etc/nginx/conf.d/proxy_params.inc;
}

location /auth/forgot-password {
    limit_req zone=login burst=3 nodelay;
    
    proxy_pass http://openmonitor_app;
    include /etc/nginx/conf.d/proxy_params.inc;
}

# =============================================================================
# API Endpoints (rate limited)
# =============================================================================

location /api/ {
    limit_req zone=api burst=50 nodelay;
    limit_conn conn_limit 50;
    
    proxy_pass http://openmonitor_app;
    include /etc/nginx/conf.d/proxy_params.inc;
    
    # Longer timeout for API requests
    proxy_read_timeout 120s;
    proxy_send_timeout 120s;
}

# NVD Sync API (longer timeout)
location /nvd/api/sync/ {
    limit_req zone=api burst=10 nodelay;
    
    proxy_pass http://openmonitor_app;
    include /etc/nginx/conf.d/proxy_params.inc;
    
    # Extended timeout for sync operations
    proxy_read_timeout 600s;
    proxy_send_timeout 600s;
}

# Report generation (longer timeout)
location /reports/api/generate {
    limit_req zone=api burst=5 nodelay;
    
    proxy_pass http://openmonitor_app;
    include /etc/nginx/conf.d/proxy_params.inc;
    
    # Extended timeout for report generation
    proxy_read_timeout 300s;
    proxy_send_timeout 300s;
}

# =============================================================================
# WebSocket Support (for real-time updates)
# =============================================================================

location /ws/ {
    proxy_pass http://openmonitor_app;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    
    # WebSocket timeout
    proxy_read_timeout 86400s;
    proxy_send_timeout 86400s;
}

# =============================================================================
# Main Application
# =============================================================================

location / {
    limit_req zone=general burst=100 nodelay;
    limit_conn conn_limit 100;
    
    proxy_pass http://openmonitor_app;
    include /etc/nginx/conf.d/proxy_params.inc;
}

# =============================================================================
# Error Pages
# =============================================================================

error_page 500 502 503 504 /50x.html;
location = /50x.html {
    root /usr/share/nginx/html;
    internal;
}

error_page 404 /404.html;
location = /404.html {
    root /usr/share/nginx/html;
    internal;
}

# Rate limit exceeded
error_page 429 /429.html;
location = /429.html {
    root /usr/share/nginx/html;
    internal;
}
