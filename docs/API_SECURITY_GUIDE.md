# API Security Configuration Guide

## Visão Geral
O Open-Monitor agora inclui camadas robustas de segurança para proteger os endpoints da API contra acesso não autorizado, ataques de força bruta e abuso.

## Funcionalidades de Segurança Implementadas

### 1. Autenticação por API Key
- **Como funciona**: Todos os endpoints sensíveis da API requerem uma chave API válida no header `X-API-Key`
- **Onde usar**: Endpoints que modificam dados (POST, PUT, DELETE) e alguns endpoints de leitura sensíveis
- **Exceções**: Health checks e dados públicos de CVEs são acessíveis sem autenticação

### 2. Rate Limiting
- **Global**: Aplicado automaticamente a todas as requisições
  - Páginas web: 200 requests/minuto
  - APIs de leitura: 100 requests/minuto
  - APIs de escrita: 30 requests/minuto
- **Por endpoint**: Limites específicos para endpoints críticos
  - Mitigação: 10 requests/minuto
  - Criação de tickets: 20 requests/minuto
  - Consultas customizadas: 10 requests/minuto

### 3. Proteção CSRF
- **Configurada**: Protege formulários web contra Cross-Site Request Forgery
- **Isenções**: Blueprints de API são automaticamente isentos

## Como Obter uma API Key

### Para Usuários Existentes
1. Faça login no sistema
2. Vá para Configurações > Perfil
3. Clique em "Gerar API Key"
4. Copie e guarde a chave gerada (ela só aparece uma vez)

### Para Novos Usuários
1. Registre-se no sistema
2. Siga os passos acima para gerar sua API key

## Como Usar a API com Autenticação

### Exemplo com curl
```bash
# Endpoint protegido
curl -X GET "https://your-domain.com/api/v1/assets" \
  -H "X-API-Key: your-api-key-here" \
  -H "Content-Type: application/json"

# Endpoint público (sem API key necessária)
curl -X GET "https://your-domain.com/api/v1/health"
```

### Exemplo com Python
```python
import requests

headers = {
    'X-API-Key': 'your-api-key-here',
    'Content-Type': 'application/json'
}

# Endpoint protegido
response = requests.get('https://your-domain.com/api/v1/assets', headers=headers)

# Endpoint público
response = requests.get('https://your-domain.com/api/v1/health')
```

## Endpoints que Requerem Autenticação

### API v1
- `GET /api/v1/risk/*` - Avaliações de risco
- `POST /api/v1/risk` - Criar avaliação de risco
- `GET /api/v1/assets` - Listar assets
- `POST /api/v1/assets` - Criar asset
- `POST /api/v1/tickets` - Criar ticket de suporte
- `POST /api/v1/vulnerabilities/*/mitigate` - Iniciar mitigação

### Analytics API
- `GET /api/v1/analytics/*` - Todos os endpoints de analytics
- `POST /api/v1/analytics/query` - Consultas customizadas

### Chatbot API
- `POST /api/chatbot/chat` - Enviar mensagens
- `GET /api/chatbot/session/*` - Gerenciar sessões
- `POST /api/chatbot/session/*/clear` - Limpar sessões

## Endpoints Públicos (Sem Autenticação)

### API v1
- `GET /api/v1/health` - Health check
- `GET /api/v1/cves` - Listar CVEs
- `GET /api/v1/cves/*` - Detalhes de CVE específico

### Chatbot API
- `GET /api/chatbot/cve/*` - Informações sobre CVE
- `GET /api/chatbot/trending` - CVEs em tendência
- `GET /api/chatbot/health` - Health check do chatbot

## Gerenciamento de API Keys

### Revogação
- Vá para Configurações > Perfil > "Revogar API Key"
- A chave será invalidada imediatamente
- Gere uma nova chave se necessário

### Segurança
- **Nunca compartilhe sua API key**
- **Use HTTPS** para todas as requisições
- **Roteie chaves comprometidas** imediatamente
- **Monitore uso** através dos logs de auditoria

## Rate Limiting

### Comportamento
- Quando o limite é excedido, você recebe HTTP 429 (Too Many Requests)
- O bloqueio é temporário (30 minutos para violações graves)
- Headers de resposta incluem informações sobre limites

### Headers de Rate Limiting
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1640995200
```

## Monitoramento e Logs

### Auditoria
- Todas as requisições autenticadas são logadas
- Tentativas de acesso não autorizado são registradas
- Uso de API keys é monitorado

### Alertas
- Limites de rate atingidos geram alertas
- Tentativas de acesso suspeitas são monitoradas
- Uso excessivo de recursos é reportado

## Suporte

Para problemas com autenticação ou rate limiting:
1. Verifique se sua API key é válida
2. Confirme que está usando o header correto (`X-API-Key`)
3. Aguarde o reset do rate limit se aplicável
4. Contate o administrador do sistema se o problema persistir