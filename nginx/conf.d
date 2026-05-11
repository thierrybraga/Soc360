server {
    listen 80;
    listen [::]:80;
    server_name _;

    # 🔒 Redirecionamento HTTP → HTTPS (Descomente em produção)
    # return 301 https://$host$request_uri;

    root /usr/share/nginx/html;
    index index.html index.htm;

    # Rate Limiting
    limit_req zone=general burst=20 nodelay;

    location / {
        try_files $uri $uri/ =404;
    }

    # Healthcheck
    location /health {
        access_log off;
        return 200 "OK\n";
        add_header Content-Type text/plain;
    }

    # Bloqueia arquivos ocultos e diretórios sensíveis
    location ~ /\. {
        deny all;
        access_log off;
        log_not_found off;
    }

    # Cache de assets estáticos
    location ~* \.(jpg|jpeg|png|gif|ico|css|js|pdf|txt|woff|woff2|svg|eot|ttf|otf)$ {
        expires 30d;
        add_header Cache-Control "public, no-transform";
        access_log off;
    }
}

# 📜 Exemplo de server HTTPS (descomente e aponte seus certs)
# server {
#     listen 443 ssl http2;
#     listen [::]:443 ssl http2;
#     server_name seu-dominio.com;
# 
#     ssl_certificate /etc/nginx/certs/fullchain.pem;
#     ssl_certificate_key /etc/nginx/certs/privkey.pem;
# 
#     # ... mesmas diretivas do server 80 ...
# }