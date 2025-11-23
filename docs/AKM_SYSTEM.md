# API Key Management System (AKM)

Sistema completo de gerenciamento multi-tenant de API Keys com escopos, rate limiting, webhooks e alertas.

## 🚀 Recursos

### Multi-tenant com Projetos
- Isolamento completo entre projetos
- Múltiplas API keys por projeto
- Estatísticas por projeto

### Sistema de Escopos (RBAC)
- Permissões granulares baseadas em escopos
- Wildcard support (`akm:projects:*` concede read/write/delete)
- 27 escopos padrão para todas as operações

### Rate Limiting Avançado
- Múltiplos níveis: por minuto, hora, dia e mês
- Configuração individual por API key
- Tracking automático de uso
- Headers X-RateLimit-* nas respostas

### Webhooks
- 15 tipos de eventos predefinidos
- Assinaturas por webhook
- Delivery com retry automático e backoff exponencial
- HMAC-SHA256 signatures para segurança
- Histórico completo de entregas

### Sistema de Alertas
- Regras customizáveis por projeto ou API key
- Múltiplos tipos de alerta (rate limit, uso, segurança)
- Operadores: gt, gte, lt, lte, eq
- Cooldown period para evitar spam
- Disparo via webhooks

### Restrições de Configuração
- IP Whitelist com suporte a CIDR notation
- Time windows (horários permitidos)
- Rate limits customizados por key

### Auditoria e Segurança
- Audit logs de todas as operações
- Tracking de uso com métricas horárias
- Correlation IDs para rastreamento
- API keys hasheadas com bcrypt

## 📋 Estrutura de Tabelas

```
akm_projects                    # Projetos multi-tenant
akm_scopes                      # Escopos de permissão
akm_api_keys                    # API keys
akm_api_key_scopes              # Associação key-scope (N:N)
akm_api_key_configs             # Configurações por key
akm_rate_limit_buckets          # Buckets para rate limiting
akm_usage_metrics               # Métricas agregadas por hora
akm_webhooks                    # Webhooks
akm_webhook_events              # Tipos de eventos
akm_webhook_subscriptions       # Assinaturas de webhooks
akm_webhook_deliveries          # Histórico de entregas
akm_alert_rules                 # Regras de alerta
akm_alert_history               # Histórico de alertas
akm_audit_logs                  # Logs de auditoria
```

## 🛠️ Setup

### 1. Executar Setup Completo

```bash
python scripts/setup_akm.py
```

Este script:
- ✅ Roda migrations do Alembic (cria todas as tabelas)
- ✅ Seeda 15 tipos de webhook events
- ✅ Seeda 27 escopos padrão
- ✅ Cria projeto admin
- ✅ Cria API key admin com escopo `akm:*`

**IMPORTANTE:** Salve a API key admin exibida - ela não será mostrada novamente!

### 2. Adicionar ao .env

```env
ADMIN_API_KEY=akm_xxxxxxxxxxxxxxxxxxxxx
```

### 3. Iniciar Aplicação

```bash
uvicorn main:app --reload
```

## 📚 API Endpoints

Todos os endpoints AKM estão sob o prefixo `/akm`:

### Projects (`/akm/projects`)
```http
POST   /akm/projects              # Criar projeto (scope: akm:projects:write)
GET    /akm/projects              # Listar projetos (scope: akm:projects:read)
GET    /akm/projects/{id}         # Obter projeto com stats (scope: akm:projects:read)
PUT    /akm/projects/{id}         # Atualizar projeto (scope: akm:projects:write)
DELETE /akm/projects/{id}         # Deletar projeto (scope: akm:projects:delete)
```

### API Keys (`/akm/keys`)
```http
POST   /akm/keys                  # Criar key (scope: akm:keys:write)
GET    /akm/keys                  # Listar keys (scope: akm:keys:read)
GET    /akm/keys/{id}             # Obter key detalhada (scope: akm:keys:read)
PUT    /akm/keys/{id}             # Atualizar metadata (scope: akm:keys:write)
PUT    /akm/keys/{id}/scopes      # Atualizar escopos (scope: akm:keys:write)
DELETE /akm/keys/{id}             # Deletar permanentemente (scope: akm:keys:delete)
POST   /akm/keys/{id}/revoke      # Revogar/desativar (scope: akm:keys:write)
```

### Scopes (`/akm/scopes`)
```http
POST   /akm/scopes                # Criar escopo (scope: akm:scopes:write)
GET    /akm/scopes                # Listar escopos (scope: akm:scopes:read)
GET    /akm/scopes/{name}         # Obter escopo (scope: akm:scopes:read)
PUT    /akm/scopes/{name}         # Atualizar escopo (scope: akm:scopes:write)
DELETE /akm/scopes/{name}         # Deletar escopo (scope: akm:scopes:delete)
```

### Webhooks (`/akm/webhooks`)
```http
POST   /akm/webhooks                           # Criar webhook (scope: akm:webhooks:write)
GET    /akm/webhooks                           # Listar webhooks (scope: akm:webhooks:read)
GET    /akm/webhooks/{id}                      # Obter webhook (scope: akm:webhooks:read)
PUT    /akm/webhooks/{id}                      # Atualizar webhook (scope: akm:webhooks:write)
DELETE /akm/webhooks/{id}                      # Deletar webhook (scope: akm:webhooks:delete)
POST   /akm/webhooks/{id}/subscriptions/{type} # Inscrever em evento (scope: akm:webhooks:write)
DELETE /akm/webhooks/{id}/subscriptions/{type} # Desinscrever (scope: akm:webhooks:write)
GET    /akm/webhooks/events/types              # Listar tipos de eventos (scope: akm:webhooks:read)
GET    /akm/webhooks/{id}/deliveries           # Listar entregas (scope: akm:webhooks:read)
GET    /akm/webhooks/deliveries/{id}           # Obter entrega (scope: akm:webhooks:read)
POST   /akm/webhooks/deliveries/{id}/retry     # Retentar entrega (scope: akm:webhooks:write)
```

### Configs (`/akm/keys/{id}/...`)
```http
GET    /akm/keys/{id}/config      # Obter configuração (scope: akm:keys:read)
PUT    /akm/keys/{id}/config      # Atualizar configuração (scope: akm:keys:write)
DELETE /akm/keys/{id}/config      # Resetar configuração (scope: akm:keys:write)
GET    /akm/keys/{id}/usage       # Obter estatísticas de uso (scope: akm:keys:read)
```

### Alerts (`/akm/alerts`)
```http
POST   /akm/alerts/rules          # Criar regra (scope: akm:alerts:write)
GET    /akm/alerts/rules          # Listar regras (scope: akm:alerts:read)
GET    /akm/alerts/rules/{id}     # Obter regra (scope: akm:alerts:read)
PUT    /akm/alerts/rules/{id}     # Atualizar regra (scope: akm:alerts:write)
DELETE /akm/alerts/rules/{id}     # Deletar regra (scope: akm:alerts:delete)
GET    /akm/alerts/history        # Listar histórico (scope: akm:alerts:read)
GET    /akm/alerts/history/{id}   # Obter item do histórico (scope: akm:alerts:read)
GET    /akm/alerts/stats          # Obter estatísticas (scope: akm:alerts:read)
```

## 🔐 Autenticação

Todas as rotas AKM requerem autenticação via header:

```http
X-API-Key: akm_xxxxxxxxxxxxxxxxxxxxx
```

A API key deve ter os escopos necessários para a operação desejada.

## 📝 Exemplos de Uso

### 1. Criar um Projeto

```bash
curl -X POST http://localhost:8000/akm/projects \
  -H "X-API-Key: $ADMIN_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My Application",
    "description": "Production application API keys"
  }'
```

### 2. Criar API Key com Escopos

```bash
curl -X POST http://localhost:8000/akm/keys \
  -H "X-API-Key: $ADMIN_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": 1,
    "name": "Frontend App Key",
    "description": "Key for React frontend",
    "scope_names": ["akm:projects:read", "akm:keys:read"],
    "expires_at": "2025-12-31T23:59:59Z"
  }'
```

**IMPORTANTE:** A resposta contém o campo `key` com a chave em plain text. Este é o único momento em que a chave é mostrada!

### 3. Configurar Rate Limits

```bash
curl -X PUT http://localhost:8000/akm/keys/2/config \
  -H "X-API-Key: $ADMIN_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "rate_limit_per_minute": 60,
    "rate_limit_per_hour": 1000,
    "rate_limit_per_day": 10000,
    "rate_limit_per_month": 300000
  }'
```

### 4. Adicionar IP Whitelist

```bash
curl -X PUT http://localhost:8000/akm/keys/2/config \
  -H "X-API-Key: $ADMIN_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "allowed_ips": ["192.168.1.0/24", "10.0.0.5"]
  }'
```

### 5. Criar Webhook

```bash
curl -X POST http://localhost:8000/akm/webhooks \
  -H "X-API-Key: $ADMIN_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": 1,
    "url": "https://myapp.com/webhooks/akm",
    "secret": "your-webhook-secret",
    "is_active": true
  }'
```

### 6. Inscrever Webhook em Eventos

```bash
# Inscrever em rate limit reached
curl -X POST http://localhost:8000/akm/webhooks/1/subscriptions/rate_limit_reached \
  -H "X-API-Key: $ADMIN_API_KEY"

# Inscrever em daily limit warning
curl -X POST http://localhost:8000/akm/webhooks/1/subscriptions/daily_limit_warning \
  -H "X-API-Key: $ADMIN_API_KEY"
```

### 7. Criar Regra de Alerta

```bash
curl -X POST http://localhost:8000/akm/alerts/rules \
  -H "X-API-Key: $ADMIN_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": 1,
    "alert_type": "usage_threshold",
    "condition_metric": "daily_usage_percent",
    "condition_operator": "gte",
    "condition_threshold": 80.0,
    "webhook_event_type": "daily_limit_warning",
    "cooldown_minutes": 60,
    "is_active": true
  }'
```

### 8. Verificar Uso da API Key

```bash
curl -X GET "http://localhost:8000/akm/keys/2/usage?start_date=2025-11-01T00:00:00Z" \
  -H "X-API-Key: $ADMIN_API_KEY"
```

## 🎯 Tipos de Webhook Events

```
rate_limit_reached          # Rate limit per minute/hour atingido
daily_limit_reached         # Limite diário atingido
monthly_limit_reached       # Limite mensal atingido
daily_limit_warning         # 80% do limite diário atingido
monthly_limit_warning       # 80% do limite mensal atingido
api_key_created             # Nova API key criada
api_key_revoked             # API key revogada
api_key_deleted             # API key deletada
api_key_config_changed      # Configuração de key alterada
suspicious_activity         # Atividade suspeita (IP/time violation)
project_created             # Novo projeto criado
project_deleted             # Projeto deletado
alert_triggered             # Regra de alerta disparada
webhook_delivery_failed     # Entrega de webhook falhou
scope_violation             # Tentativa de acesso sem escopo
```

## 🔍 Wildcard Scopes

O sistema suporta wildcards para escopos hierárquicos:

```
akm:*                    # Acesso total ao sistema
akm:projects:*           # Todos os escopos de projects (read/write/delete)
akm:keys:*               # Todos os escopos de keys
akm:webhooks:*           # Todos os escopos de webhooks
akm:alerts:*             # Todos os escopos de alerts
akm:admin:*              # Todos os escopos de admin
```

## 🛡️ Segurança

- **API Keys hasheadas:** Bcrypt com salt
- **Webhook signatures:** HMAC-SHA256 com secret
- **IP Whitelist:** Suporte a CIDR notation
- **Time restrictions:** Janelas de horário permitido
- **Scope-based RBAC:** Controle granular de permissões
- **Audit logs:** Tracking completo de operações

## 📊 Rate Limiting Headers

Toda resposta de endpoints protegidos inclui headers de rate limiting:

```http
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 873
X-RateLimit-Reset: 1732137600
```

## 🧪 Testing

Após o setup, teste os endpoints:

```bash
# Health check
curl http://localhost:8000/health

# Listar projetos (com admin key)
curl http://localhost:8000/akm/projects \
  -H "X-API-Key: $ADMIN_API_KEY"

# Ver documentação interativa
open http://localhost:8000/docs
```

## 📖 Documentação API

- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc

## 🔄 Workflow Típico

1. **Criar Projeto** para seu aplicativo
2. **Criar API Keys** para diferentes ambientes (dev/prod)
3. **Configurar Escopos** específicos para cada key
4. **Definir Rate Limits** apropriados
5. **Configurar Webhooks** para notificações
6. **Criar Alertas** para monitoramento proativo
7. **Monitorar Uso** via endpoints de stats

## 🚨 Troubleshooting

### API Key não funciona
- Verifique se a key está ativa (`is_active=True`)
- Verifique se não expirou (`expires_at`)
- Verifique se tem os escopos necessários
- Verifique IP whitelist e time restrictions

### Rate limit atingido
- Verifique configuração em `/keys/{id}/config`
- Verifique uso atual em `/keys/{id}/usage`
- Aguarde o reset (veja header `X-RateLimit-Reset`)

### Webhook não entrega
- Verifique se webhook está ativo
- Verifique se está inscrito no evento
- Verifique logs em `/webhooks/{id}/deliveries`
- Verifique URL e secret

## 📝 License

MIT License
