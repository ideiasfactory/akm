# 🔐 Sistema de Auditoria e Logging

Documentação completa do sistema de auditoria com integridade criptográfica e rastreamento de operações.

## 📋 Índice

- [Visão Geral](#visão-geral)
- [Características](#características)
- [Arquitetura](#arquitetura)
- [Modelo de Dados](#modelo-de-dados)
- [Logging Automático](#logging-automático)
- [API de Consulta](#api-de-consulta)
- [Verificação de Integridade](#verificação-de-integridade)
- [Exemplos de Uso](#exemplos-de-uso)
- [Segurança](#segurança)
- [Melhores Práticas](#melhores-práticas)

## 🎯 Visão Geral

O sistema de auditoria do AKM fornece um **trail de auditoria imutável** com proteção de integridade criptográfica para todas as operações sensíveis.

### Principais Recursos

✅ **Logging Automático**: Middleware captura todas as requisições automaticamente  
✅ **Correlation IDs**: Rastreamento de operações relacionadas  
✅ **Integridade Criptográfica**: Hash SHA-256 para detectar adulterações  
✅ **Precisão de Microsegundos**: Timestamps com precisão de microsegundos  
✅ **Sanitização Automática**: Remove dados sensíveis (senhas, tokens, etc.)  
✅ **Multi-Tenancy**: Filtragem por projeto para isolamento  
✅ **Read-Only API**: Endpoints apenas leitura para preservar integridade  
✅ **Console + Database**: Logs em console (JSON) e banco de dados PostgreSQL  

## 🏗️ Características

### 1. Auditoria Automática

```python
# Middleware captura automaticamente todas as requisições
# Nenhum código adicional necessário nas rotas!

@router.post("/projects")
async def create_project(...):
    # Auditoria acontece automaticamente
    # correlation_id disponível em request.state.correlation_id
    return project
```

### 2. Correlation IDs

Agrupa operações relacionadas:

```
correlation_id: 550e8400-e29b-41d4-a716-446655440000
  ├─ Operation 1: authenticate (2024-11-20 10:00:00.123456)
  ├─ Operation 2: authorize (2024-11-20 10:00:00.234567)
  └─ Operation 3: create_project (2024-11-20 10:00:00.345678)
```

### 3. Proteção de Integridade

```python
# Cada audit log tem um hash SHA-256
entry_hash = sha256(
    correlation_id + timestamp + operation + 
    resource_type + resource_id + api_key_id + 
    request_payload + response_status + ...
)

# Verificação
if entry.entry_hash == entry.calculate_hash():
    print("✓ Integridade verificada")
else:
    print("⚠️ VIOLAÇÃO: Log foi adulterado!")
```

## 🗄️ Modelo de Dados

### Tabela: `akm_audit_logs`

```sql
CREATE TABLE akm_audit_logs (
    -- Identity
    id SERIAL PRIMARY KEY,
    correlation_id VARCHAR(36) UNIQUE NOT NULL,  -- UUID
    entry_hash VARCHAR(64) NOT NULL,              -- SHA-256
    
    -- Authentication Context
    api_key_id INTEGER REFERENCES akm_api_keys(id),
    project_id INTEGER REFERENCES akm_projects(id),
    
    -- Operation Details
    operation VARCHAR(100) NOT NULL,              -- create_api_key, delete_project
    action VARCHAR(50) NOT NULL,                  -- POST, DELETE, AUTH
    resource_type VARCHAR(50) NOT NULL,           -- api_key, project, scope
    resource_id VARCHAR(100),                     -- Resource identifier
    
    -- Request Context
    endpoint VARCHAR(255) NOT NULL,               -- /akm/projects
    http_method VARCHAR(10) NOT NULL,             -- GET, POST, PUT, DELETE
    ip_address VARCHAR(45),                       -- IPv6 support
    user_agent VARCHAR(500),
    
    -- Request/Response Data (sanitized)
    request_payload JSONB,
    response_status INTEGER,                      -- HTTP status code
    response_payload JSONB,
    error_message TEXT,
    
    -- Metadata
    metadata JSONB,                               -- Extra context
    
    -- Timestamps
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,  -- Microsecond precision
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Status
    status VARCHAR(20) NOT NULL DEFAULT 'success' -- success, failure, denied
);

-- Indexes for efficient querying
CREATE INDEX idx_audit_timestamp ON akm_audit_logs(timestamp DESC);
CREATE INDEX idx_audit_project_time ON akm_audit_logs(project_id, timestamp DESC);
CREATE INDEX idx_audit_correlation ON akm_audit_logs(correlation_id);
CREATE INDEX idx_audit_hash ON akm_audit_logs(entry_hash);
```

### Campos Principais

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `correlation_id` | UUID | Agrupa operações relacionadas |
| `entry_hash` | SHA-256 | Hash para verificação de integridade |
| `operation` | String | Nome da operação (ex: `create_api_key`) |
| `action` | String | Método HTTP ou tipo de ação |
| `resource_type` | String | Tipo do recurso afetado |
| `resource_id` | String | ID do recurso |
| `status` | Enum | `success`, `failure`, `denied` |
| `timestamp` | DateTime | Timestamp com microsegundos |
| `ip_address` | String | IP do cliente (IPv4/IPv6) |
| `request_payload` | JSON | Corpo da requisição (sanitizado) |
| `response_status` | Integer | HTTP status code |
| `metadata` | JSON | Contexto adicional |

## 🤖 Logging Automático

### Middleware de Auditoria

O `AuditMiddleware` captura automaticamente todas as requisições:

```python
# src/middleware/audit.py

class AuditMiddleware(BaseHTTPMiddleware):
    """Audita automaticamente todas as requisições."""
    
    async def dispatch(self, request: Request, call_next):
        # 1. Gera correlation_id
        correlation_id = generate_correlation_id()
        request.state.correlation_id = correlation_id
        
        # 2. Captura request body (sanitizado)
        request_payload = await capture_request(request)
        
        # 3. Processa request
        response = await call_next(request)
        
        # 4. Registra no audit log
        await log_to_database(
            correlation_id=correlation_id,
            operation=infer_operation(request.path, request.method),
            request=request,
            response=response,
            request_payload=sanitize(request_payload)
        )
        
        # 5. Adiciona correlation_id ao response
        response.headers["X-Correlation-ID"] = correlation_id
        
        return response
```

### Paths Excluídos

Alguns paths não são auditados (por performance):

```python
EXCLUDED_PATHS = {
    "/health", "/healthz", "/ready",
    "/docs", "/redoc", "/openapi.json",
    "/favicon.ico"
}

EXCLUDED_METHODS = {"OPTIONS", "HEAD"}
```

### Sanitização Automática

Campos sensíveis são automaticamente removidos:

```python
SENSITIVE_FIELDS = {
    "password", "token", "secret", "api_key", 
    "key_hash", "authorization", "x-api-key", 
    "bearer", "credential", "private_key", 
    "client_secret"
}

# Antes da sanitização
{
    "username": "admin",
    "password": "secret123",  # ← sensível
    "api_key": "sk_prod_xyz"  # ← sensível
}

# Depois da sanitização
{
    "username": "admin",
    "password": "[REDACTED]",
    "api_key": "[REDACTED]"
}
```

## 📡 API de Consulta

### Scope Necessário

Todos os endpoints de auditoria requerem o scope especial:

```
akm:audit:read
```

### Endpoints Disponíveis

#### 1. Listar Audit Logs

```http
GET /akm/audit/logs?project_id=1&limit=100&offset=0
X-API-Key: your_admin_key
```

**Filtros disponíveis:**
- `project_id`: Filtrar por projeto
- `api_key_id`: Filtrar por API key
- `operation`: Filtrar por operação (ex: `create_api_key`)
- `resource_type`: Filtrar por tipo de recurso
- `resource_id`: Filtrar por ID do recurso
- `status`: Filtrar por status (`success`, `failure`, `denied`)
- `ip_address`: Filtrar por IP
- `start_date`: Data inicial (ISO 8601)
- `end_date`: Data final (ISO 8601)
- `limit`: Máximo de resultados (1-1000)
- `offset`: Paginação

**Response:**
```json
{
  "total": 1523,
  "limit": 100,
  "offset": 0,
  "logs": [
    {
      "id": 1523,
      "correlation_id": "550e8400-e29b-41d4-a716-446655440000",
      "operation": "create_api_key",
      "resource_type": "api_key",
      "resource_id": "123",
      "status": "success",
      "timestamp": "2024-11-20T10:00:00.123456Z",
      "ip_address": "192.168.1.100",
      "api_key_id": 5,
      "project_id": 1,
      "response_status": 201
    }
  ]
}
```

#### 2. Obter Audit Log Específico

```http
GET /akm/audit/logs/1523
X-API-Key: your_admin_key
```

**Response:**
```json
{
  "id": 1523,
  "correlation_id": "550e8400-e29b-41d4-a716-446655440000",
  "entry_hash": "a3f5d8c9...",
  "operation": "create_api_key",
  "action": "POST",
  "resource_type": "api_key",
  "resource_id": "123",
  "endpoint": "/akm/keys",
  "http_method": "POST",
  "ip_address": "192.168.1.100",
  "user_agent": "Mozilla/5.0...",
  "request_payload": {
    "project_id": 1,
    "name": "Production API Key",
    "scope_names": ["akm:keys:read"]
  },
  "response_status": 201,
  "response_payload": {
    "id": 123,
    "key": "[REDACTED]",
    "name": "Production API Key"
  },
  "metadata": {
    "duration_ms": 45.23,
    "content_type": "application/json"
  },
  "timestamp": "2024-11-20T10:00:00.123456Z",
  "status": "success",
  "api_key_id": 5,
  "project_id": 1
}
```

#### 3. Operações Correlacionadas

```http
GET /akm/audit/correlation/{correlation_id}
X-API-Key: your_admin_key
```

**Response:**
```json
{
  "correlation_id": "550e8400-e29b-41d4-a716-446655440000",
  "operation_count": 3,
  "operations": [
    {
      "id": 1521,
      "operation": "authenticate",
      "timestamp": "2024-11-20T10:00:00.123456Z",
      "status": "success"
    },
    {
      "id": 1522,
      "operation": "authorize",
      "timestamp": "2024-11-20T10:00:00.234567Z",
      "status": "success"
    },
    {
      "id": 1523,
      "operation": "create_api_key",
      "timestamp": "2024-11-20T10:00:00.345678Z",
      "status": "success"
    }
  ],
  "first_timestamp": "2024-11-20T10:00:00.123456Z",
  "last_timestamp": "2024-11-20T10:00:00.345678Z",
  "all_successful": true
}
```

#### 4. Atividade do Recurso

```http
GET /akm/audit/resource/{resource_type}/{resource_id}?limit=50
X-API-Key: your_admin_key
```

**Exemplo:**
```bash
GET /akm/audit/resource/api_key/123
```

**Response:**
```json
{
  "resource_type": "api_key",
  "resource_id": "123",
  "activity_count": 15,
  "activities": [
    {
      "id": 1523,
      "operation": "create_api_key",
      "timestamp": "2024-11-20T10:00:00.123456Z",
      "status": "success"
    },
    {
      "id": 1545,
      "operation": "update_api_key",
      "timestamp": "2024-11-20T11:30:00.123456Z",
      "status": "success"
    }
  ],
  "first_activity": "2024-11-20T10:00:00.123456Z",
  "last_activity": "2024-11-20T14:25:00.123456Z"
}
```

#### 5. Estatísticas de Auditoria

```http
GET /akm/audit/statistics?project_id=1&hours=24
X-API-Key: your_admin_key
```

**Response:**
```json
{
  "total_operations": 1523,
  "successful_operations": 1450,
  "failed_operations": 45,
  "denied_operations": 28,
  "unique_projects": 5,
  "unique_api_keys": 12,
  "unique_ip_addresses": 8,
  "operations_by_type": [
    {
      "operation": "create_api_key",
      "status": "success",
      "count": 145
    },
    {
      "operation": "authenticate",
      "status": "success",
      "count": 1205
    },
    {
      "operation": "delete_project",
      "status": "denied",
      "count": 12
    }
  ],
  "start_date": "2024-11-19T10:00:00Z",
  "end_date": "2024-11-20T10:00:00Z"
}
```

#### 6. Operações Falhadas Recentes

```http
GET /akm/audit/failed?hours=24&limit=50
X-API-Key: your_admin_key
```

**Response:**
```json
[
  {
    "id": 1520,
    "operation": "delete_project",
    "status": "denied",
    "timestamp": "2024-11-20T09:45:00.123456Z",
    "error_message": "Insufficient permissions",
    "ip_address": "192.168.1.100"
  }
]
```

## 🔒 Verificação de Integridade

### Verificar Log Individual

```http
GET /akm/audit/integrity/verify/1523
X-API-Key: your_admin_key
```

**Response (Íntegro):**
```json
{
  "verified": true,
  "audit_id": 1523,
  "correlation_id": "550e8400-e29b-41d4-a716-446655440000",
  "stored_hash": "a3f5d8c9b2e1...",
  "calculated_hash": "a3f5d8c9b2e1...",
  "timestamp": "2024-11-20T10:00:00.123456Z",
  "message": "Integrity verified"
}
```

**Response (Adulterado):**
```json
{
  "verified": false,
  "audit_id": 1523,
  "correlation_id": "550e8400-e29b-41d4-a716-446655440000",
  "stored_hash": "a3f5d8c9b2e1...",
  "calculated_hash": "b4e6c7a8d3f2...",
  "timestamp": "2024-11-20T10:00:00.123456Z",
  "message": "INTEGRITY VIOLATION: Hash mismatch detected"
}
```

### Verificação em Massa

```http
GET /akm/audit/integrity/bulk-verify?limit=1000
X-API-Key: your_admin_key
```

**Response:**
```json
{
  "total_verified": 1000,
  "passed": 998,
  "failed": 2,
  "integrity_score": 99.8,
  "violations": [
    {
      "audit_id": 523,
      "correlation_id": "...",
      "operation": "delete_project",
      "timestamp": "2024-11-19T15:30:00Z",
      "stored_hash": "abc123...",
      "calculated_hash": "def456..."
    },
    {
      "audit_id": 824,
      "correlation_id": "...",
      "operation": "update_api_key",
      "timestamp": "2024-11-20T08:15:00Z",
      "stored_hash": "xyz789...",
      "calculated_hash": "uvw012..."
    }
  ]
}
```

## 💻 Exemplos de Uso

### Exemplo 1: Rastrear Todas as Ações de um Usuário

```bash
#!/bin/bash

API_KEY="your_admin_key"
PROJECT_ID=1

# Listar todas as operações do projeto nas últimas 24h
curl -X GET "http://localhost:8000/akm/audit/logs?project_id=$PROJECT_ID&hours=24&limit=500" \
  -H "X-API-Key: $API_KEY" | jq '.logs[] | {
    operation,
    timestamp,
    ip_address,
    status
  }'
```

### Exemplo 2: Investigar Operações Falhadas

```bash
# Buscar todas as operações falhadas ou negadas
curl -X GET "http://localhost:8000/akm/audit/failed?hours=168&limit=100" \
  -H "X-API-Key: $API_KEY" | jq '.[] | {
    operation,
    timestamp,
    status,
    error_message,
    ip_address
  }'
```

### Exemplo 3: Auditoria de Compliance

```python
import httpx
from datetime import datetime, timedelta

API_KEY = "your_admin_key"
BASE_URL = "http://localhost:8000/akm"

async def generate_compliance_report(project_id: int, days: int = 30):
    """Gera relatório de compliance para auditoria."""
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    
    async with httpx.AsyncClient() as client:
        # 1. Obter estatísticas
        stats_response = await client.get(
            f"{BASE_URL}/audit/statistics",
            params={"project_id": project_id, "hours": days * 24},
            headers={"X-API-Key": API_KEY}
        )
        stats = stats_response.json()
        
        # 2. Verificar integridade
        integrity_response = await client.get(
            f"{BASE_URL}/audit/integrity/bulk-verify",
            params={"project_id": project_id, "limit": 10000},
            headers={"X-API-Key": API_KEY}
        )
        integrity = integrity_response.json()
        
        # 3. Obter operações críticas
        critical_ops = await client.get(
            f"{BASE_URL}/audit/logs",
            params={
                "project_id": project_id,
                "operation": "delete_api_key",
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "limit": 1000
            },
            headers={"X-API-Key": API_KEY}
        )
        deletes = critical_ops.json()
        
        # 4. Gerar relatório
        report = {
            "period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat(),
                "days": days
            },
            "statistics": {
                "total_operations": stats["total_operations"],
                "success_rate": (stats["successful_operations"] / stats["total_operations"] * 100) if stats["total_operations"] > 0 else 0,
                "unique_users": stats["unique_api_keys"],
                "unique_ips": stats["unique_ip_addresses"]
            },
            "integrity": {
                "score": integrity["integrity_score"],
                "violations": len(integrity["violations"]),
                "status": "PASS" if integrity["integrity_score"] >= 99.9 else "FAIL"
            },
            "critical_operations": {
                "deletions": deletes["total"],
                "details": deletes["logs"][:10]  # Top 10
            }
        }
        
        return report

# Uso
report = await generate_compliance_report(project_id=1, days=30)
print(json.dumps(report, indent=2))
```

### Exemplo 4: Monitoramento em Tempo Real

```python
import asyncio
from datetime import datetime, timedelta

async def monitor_suspicious_activity():
    """Monitora atividades suspeitas em tempo real."""
    
    while True:
        # Verificar operações falhadas na última hora
        failed = await get_failed_operations(hours=1)
        
        # Alertar se muitas falhas
        if len(failed) > 10:
            print(f"⚠️  ALERTA: {len(failed)} operações falhadas na última hora")
            
            # Agrupar por IP
            ips = {}
            for op in failed:
                ip = op["ip_address"]
                ips[ip] = ips.get(ip, 0) + 1
            
            # IPs com mais de 5 falhas
            suspicious_ips = {ip: count for ip, count in ips.items() if count > 5}
            
            if suspicious_ips:
                print(f"🚨 IPs suspeitos: {suspicious_ips}")
                # Aqui você poderia bloquear automaticamente ou enviar alerta
        
        # Aguardar 5 minutos
        await asyncio.sleep(300)
```

## 🛡️ Segurança

### 1. Acesso Restrito

- **Scope Especial**: Apenas chaves com `akm:audit:read` podem acessar logs
- **Read-Only**: Nenhuma operação de escrita/atualização/exclusão permitida
- **Project Isolation**: Usuários só veem logs de seus projetos (a menos que seja admin)

### 2. Proteção de Integridade

```python
# Cada log tem hash SHA-256 de seus dados
# Qualquer alteração invalida o hash

def calculate_hash(audit_entry):
    hash_data = {
        "correlation_id": audit_entry.correlation_id,
        "timestamp": audit_entry.timestamp.isoformat(),
        "operation": audit_entry.operation,
        "resource_type": audit_entry.resource_type,
        "resource_id": audit_entry.resource_id,
        "api_key_id": audit_entry.api_key_id,
        "request_payload": audit_entry.request_payload,
        "response_status": audit_entry.response_status,
        # ... mais campos
    }
    
    hash_string = json.dumps(hash_data, sort_keys=True, default=str)
    return hashlib.sha256(hash_string.encode('utf-8')).hexdigest()
```

### 3. Sanitização de Dados

```python
# Remove automaticamente dados sensíveis antes de salvar
SENSITIVE_FIELDS = {
    "password", "token", "secret", "api_key",
    "key_hash", "authorization", "bearer",
    "credential", "private_key", "client_secret"
}

# Exemplo de sanitização recursiva
def sanitize_data(data):
    if isinstance(data, dict):
        sanitized = {}
        for key, value in data.items():
            if any(sensitive in key.lower() for sensitive in SENSITIVE_FIELDS):
                sanitized[key] = "[REDACTED]"
            else:
                sanitized[key] = sanitize_data(value)
        return sanitized
    elif isinstance(data, list):
        return [sanitize_data(item) for item in data]
    else:
        return data
```

## ✅ Melhores Práticas

### 1. Retenção de Logs

```python
# Script de limpeza (executar mensalmente)
from datetime import datetime, timedelta

async def cleanup_old_audit_logs(retention_days: int = 90):
    """Remove audit logs mais antigos que retention_days."""
    
    cutoff_date = datetime.now() - timedelta(days=retention_days)
    
    # IMPORTANTE: Exportar para backup antes de deletar
    await export_audit_logs_to_s3(end_date=cutoff_date)
    
    # Deletar logs antigos
    await db.execute(
        "DELETE FROM akm_audit_logs WHERE timestamp < :cutoff",
        {"cutoff": cutoff_date}
    )
```

### 2. Monitoramento de Integridade

```bash
#!/bin/bash
# Executar diariamente via cron

API_KEY="your_admin_key"

# Verificar integridade dos últimos 1000 logs
RESULT=$(curl -s -X GET \
  "http://localhost:8000/akm/audit/integrity/bulk-verify?limit=1000" \
  -H "X-API-Key: $API_KEY")

SCORE=$(echo $RESULT | jq -r '.integrity_score')

# Alertar se score < 100%
if (( $(echo "$SCORE < 100" | bc -l) )); then
  echo "⚠️  ALERTA: Integrity score: $SCORE%"
  echo $RESULT | jq '.violations'
  
  # Enviar para sistema de alertas
  # send_alert_to_slack/pagerduty/etc
fi
```

### 3. Análise de Tendências

```python
async def analyze_security_trends(project_id: int):
    """Analisa tendências de segurança ao longo do tempo."""
    
    # Últimos 7 dias
    stats_7d = await get_statistics(project_id, hours=168)
    
    # Últimos 30 dias
    stats_30d = await get_statistics(project_id, hours=720)
    
    # Calcular tendências
    trends = {
        "authentication_failures": {
            "7d": count_operations(stats_7d, "authenticate", "denied"),
            "30d_avg": count_operations(stats_30d, "authenticate", "denied") / 30 * 7
        },
        "unique_ips": {
            "7d": stats_7d["unique_ip_addresses"],
            "30d_avg": stats_30d["unique_ip_addresses"] / 30 * 7
        }
    }
    
    # Detectar anomalias
    if trends["authentication_failures"]["7d"] > trends["authentication_failures"]["30d_avg"] * 2:
        print("⚠️  ANOMALIA: Aumento significativo em falhas de autenticação")
    
    return trends
```

### 4. Compliance e Relatórios

```python
# Gerar relatórios mensais para compliance
async def generate_monthly_compliance_report():
    """Gera relatório de compliance para auditorias externas."""
    
    report = {
        "period": get_last_month(),
        "audit_coverage": {
            "total_operations": await count_all_operations(),
            "logged_operations": await count_logged_operations(),
            "coverage_percentage": 100.0  # 100% de cobertura
        },
        "integrity_verification": {
            "logs_verified": 10000,
            "passed": 10000,
            "failed": 0,
            "score": 100.0
        },
        "security_incidents": await get_security_incidents(),
        "access_patterns": await analyze_access_patterns(),
        "recommendations": generate_recommendations()
    }
    
    # Exportar para PDF
    generate_pdf_report(report, filename=f"compliance_report_{get_last_month()}.pdf")
```

## 📊 Logs no Console

Além do banco de dados, todos os audit logs também são escritos no console em formato JSON estruturado:

```json
{
  "timestamp": "2024-11-20T10:00:00.123456Z",
  "level": "INFO",
  "logger": "audit",
  "message": "AUDIT: create_api_key",
  "audit_type": "operation",
  "correlation_id": "550e8400-e29b-41d4-a716-446655440000",
  "operation": "create_api_key",
  "resource_type": "api_key",
  "resource_id": "123",
  "action": "POST",
  "status": "success",
  "api_key_id": 5,
  "project_id": 1,
  "ip_address": "192.168.1.100",
  "endpoint": "/akm/keys",
  "http_method": "POST",
  "response_status": 201,
  "entry_hash": "a3f5d8c9b2e1...",
  "metadata": {
    "duration_ms": 45.23
  }
}
```

Isso permite integração com sistemas como:
- **BetterStack / Logtail**: Agregação e análise de logs
- **ELK Stack**: Elasticsearch, Logstash, Kibana
- **Splunk**: Análise de segurança
- **Datadog**: Monitoramento e alertas

## 🎓 Resumo

O sistema de auditoria do AKM fornece:

✅ **Rastreabilidade completa** de todas as operações  
✅ **Proteção contra adulteração** com hash criptográfico  
✅ **Correlation IDs** para rastreamento de transações  
✅ **API read-only** para consulta segura  
✅ **Sanitização automática** de dados sensíveis  
✅ **Multi-tenancy** com isolamento por projeto  
✅ **Verificação de integridade** individual e em massa  
✅ **Logs estruturados** em console + database  

Para suporte ou dúvidas, consulte a documentação adicional em `docs/`.
