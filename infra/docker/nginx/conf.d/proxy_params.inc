# Open-Monitor v3.0 - Proxy Parameters
# Common proxy settings for upstream connections

# HTTP version for keepalive
proxy_http_version 1.1;

# Headers
proxy_set_header Host $host;
proxy_set_header X-Real-IP $remote_addr;
proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
proxy_set_header X-Forwarded-Proto $scheme;
proxy_set_header X-Forwarded-Host $host;
proxy_set_header X-Forwarded-Port $server_port;
proxy_set_header X-Request-ID $request_id;

# Connection settings
proxy_set_header Connection "";

# Buffering
proxy_buffering on;
proxy_buffer_size 4k;
proxy_buffers 8 4k;
proxy_busy_buffers_size 8k;

# Timeouts (handled in locations.conf or defaults)
# proxy_connect_timeout 30s;
# proxy_send_timeout 60s;
# proxy_read_timeout 60s;

# Error handling
proxy_intercept_errors off;
proxy_next_upstream error timeout invalid_header http_500 http_502 http_503 http_504;
proxy_next_upstream_timeout 10s;
proxy_next_upstream_tries 2;

# Don't pass cookies for static content
# proxy_hide_header Set-Cookie;
# proxy_ignore_headers Set-Cookie;
