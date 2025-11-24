# 🚀 Guia Rápido - Sistema de Auditoria

Guia prático para começar a usar o sistema de auditoria do AKM.

## ⚡ Setup Rápido

### 1. Executar Migration

```bash
# Aplicar migration de auditoria
alembic upgrade head
```

### 2. Importar Scopes de Auditoria

```bash
# Importar scopes atualizados (inclui akm:audit:read)
python scripts/import_scopes.py data/scopes.json
```

### 3. Criar API Key com Acesso de Auditoria

```bash
# Criar chave com permissão de auditoria
curl -X POST http://localhost:8000/akm/keys \
  -H "X-API-Key: $ADMIN_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": 1,
    "name": "Audit Viewer Key",
    "scope_names": ["akm:audit:read", "akm:audit:verify"],
    "description": "Key for viewing audit logs"
  }'

# Salvar a chave retornada
AUDIT_KEY="<key_gerada>"
```

## 📋 Casos de Uso Comuns

### Ver Últimas Operações

```bash
# Últimas 50 operações
curl -X GET "http://localhost:8000/akm/audit/logs?limit=50" \
  -H "X-API-Key: $AUDIT_KEY" | jq '.logs[] | {operation, status, timestamp}'
```

### Rastrear Operações de um Projeto

```bash
# Todas as operações do projeto 1
curl -X GET "http://localhost:8000/akm/audit/logs?project_id=1&limit=100" \
  -H "X-API-Key: $AUDIT_KEY" | jq '.logs'
```

### Ver Operações Falhadas

```bash
# Operações que falharam nas últimas 24h
curl -X GET "http://localhost:8000/akm/audit/failed?hours=24" \
  -H "X-API-Key: $AUDIT_KEY" | jq '.[] | {operation, error_message, ip_address, timestamp}'
```

### Verificar Integridade

```bash
# Verificar integridade dos últimos 1000 logs
curl -X GET "http://localhost:8000/akm/audit/integrity/bulk-verify?limit=1000" \
  -H "X-API-Key: $AUDIT_KEY" | jq '{score: .integrity_score, violations: .failed}'
```

### Estatísticas de Uso

```bash
# Estatísticas das últimas 24h
curl -X GET "http://localhost:8000/akm/audit/statistics?hours=24" \
  -H "X-API-Key: $AUDIT_KEY" | jq '{
    total: .total_operations,
    success: .successful_operations,
    failed: .failed_operations,
    denied: .denied_operations
  }'
```

### Rastrear Atividade de um Recurso

```bash
# Ver histórico de uma API key específica
curl -X GET "http://localhost:8000/akm/audit/resource/api_key/123" \
  -H "X-API-Key: $AUDIT_KEY" | jq '.activities[] | {operation, timestamp, status}'
```

### Ver Operações Correlacionadas

```bash
# Obter correlation_id de uma requisição
CORRELATION_ID="550e8400-e29b-41d4-a716-446655440000"

# Ver todas as operações relacionadas
curl -X GET "http://localhost:8000/akm/audit/correlation/$CORRELATION_ID" \
  -H "X-API-Key: $AUDIT_KEY" | jq '.operations'
```

## 🔍 Exemplos de Queries Avançadas

### Buscar Operações de Deleção

```bash
curl -X GET "http://localhost:8000/akm/audit/logs?operation=delete_api_key&limit=100" \
  -H "X-API-Key: $AUDIT_KEY"
```

### Buscar por IP Específico

```bash
curl -X GET "http://localhost:8000/akm/audit/logs?ip_address=192.168.1.100&limit=50" \
  -H "X-API-Key: $AUDIT_KEY"
```

### Buscar por Data Range

```bash
# Operações entre 19 e 20 de novembro
curl -X GET "http://localhost:8000/akm/audit/logs" \
  -H "X-API-Key: $AUDIT_KEY" \
  -G --data-urlencode "start_date=2024-11-19T00:00:00Z" \
  --data-urlencode "end_date=2024-11-20T23:59:59Z"
```

## 📊 Dashboard Simples

Script Python para dashboard em tempo real:

```python
import httpx
import asyncio
from rich.console import Console
from rich.table import Table
from datetime import datetime

console = Console()
API_KEY = "your_audit_key"
BASE_URL = "http://localhost:8000/akm"

async def show_dashboard():
    """Exibe dashboard de auditoria."""
    
    async with httpx.AsyncClient() as client:
        # Estatísticas das últimas 24h
        stats_resp = await client.get(
            f"{BASE_URL}/audit/statistics?hours=24",
            headers={"X-API-Key": API_KEY}
        )
        stats = stats_resp.json()
        
        # Operações falhadas
        failed_resp = await client.get(
            f"{BASE_URL}/audit/failed?hours=24&limit=10",
            headers={"X-API-Key": API_KEY}
        )
        failed = failed_resp.json()
        
        # Verificar integridade
        integrity_resp = await client.get(
            f"{BASE_URL}/audit/integrity/bulk-verify?limit=1000",
            headers={"X-API-Key": API_KEY}
        )
        integrity = integrity_resp.json()
        
        # Exibir dashboard
        console.clear()
        console.print("\n[bold cyan]📊 Audit Dashboard - Last 24h[/bold cyan]\n")
        
        # Estatísticas
        table = Table(title="Statistics")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")
        
        table.add_row("Total Operations", str(stats["total_operations"]))
        table.add_row("Successful", str(stats["successful_operations"]))
        table.add_row("Failed", str(stats["failed_operations"]))
        table.add_row("Denied", str(stats["denied_operations"]))
        table.add_row("Success Rate", f"{stats['successful_operations'] / stats['total_operations'] * 100:.2f}%")
        
        console.print(table)
        console.print()
        
        # Integridade
        console.print(f"[bold]🔒 Integrity Score:[/bold] {integrity['integrity_score']:.2f}%")
        if integrity['failed'] > 0:
            console.print(f"[red]⚠️  {integrity['failed']} violations detected![/red]")
        else:
            console.print("[green]✓ All logs verified[/green]")
        
        console.print()
        
        # Operações falhadas
        if failed:
            console.print("[bold red]⚠️  Recent Failures:[/bold red]")
            for op in failed[:5]:
                console.print(f"  • {op['operation']} - {op['error_message']} ({op['ip_address']})")

# Executar
asyncio.run(show_dashboard())
```

## 🛠️ Scripts Úteis

### Script 1: Exportar Logs para CSV

```python
import csv
from datetime import datetime, timedelta

async def export_audit_logs_to_csv(project_id: int, days: int = 7):
    """Exporta audit logs para CSV."""
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{BASE_URL}/audit/logs",
            params={
                "project_id": project_id,
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "limit": 10000
            },
            headers={"X-API-Key": API_KEY}
        )
        
        logs = response.json()["logs"]
        
        # Escrever CSV
        with open(f"audit_logs_{project_id}_{days}d.csv", "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=[
                "id", "timestamp", "operation", "resource_type", 
                "status", "ip_address", "api_key_id"
            ])
            writer.writeheader()
            
            for log in logs:
                writer.writerow({
                    "id": log["id"],
                    "timestamp": log["timestamp"],
                    "operation": log["operation"],
                    "resource_type": log["resource_type"],
                    "status": log["status"],
                    "ip_address": log.get("ip_address"),
                    "api_key_id": log.get("api_key_id")
                })
        
        print(f"✓ Exported {len(logs)} logs to audit_logs_{project_id}_{days}d.csv")

# Uso
await export_audit_logs_to_csv(project_id=1, days=30)
```

### Script 2: Alertas de Segurança

```python
async def check_security_alerts():
    """Verifica e alerta sobre atividades suspeitas."""
    
    # Operações falhadas na última hora
    failed = await get_failed_operations(hours=1)
    
    # Agrupar por IP
    ip_failures = {}
    for op in failed:
        ip = op["ip_address"]
        ip_failures[ip] = ip_failures.get(ip, [])
        ip_failures[ip].append(op)
    
    # Alertar IPs com mais de 5 falhas
    for ip, ops in ip_failures.items():
        if len(ops) >= 5:
            print(f"🚨 ALERT: IP {ip} has {len(ops)} failed operations in last hour")
            print(f"   Operations: {[op['operation'] for op in ops]}")
            
            # Aqui você pode:
            # - Bloquear IP temporariamente
            # - Enviar notificação
            # - Criar ticket de segurança
```

### Script 3: Monitoramento Contínuo

```bash
#!/bin/bash
# monitor_audit.sh

API_KEY="your_audit_key"

while true; do
    # Verificar integridade
    INTEGRITY=$(curl -s -X GET \
      "http://localhost:8000/akm/audit/integrity/bulk-verify?limit=100" \
      -H "X-API-Key: $API_KEY" | jq -r '.integrity_score')
    
    # Contar operações falhadas
    FAILED=$(curl -s -X GET \
      "http://localhost:8000/akm/audit/failed?hours=1" \
      -H "X-API-Key: $API_KEY" | jq 'length')
    
    echo "$(date) - Integrity: $INTEGRITY% - Failed: $FAILED"
    
    # Alertar se problemas
    if (( $(echo "$INTEGRITY < 100" | bc -l) )); then
        echo "⚠️  INTEGRITY VIOLATION!"
    fi
    
    if [ "$FAILED" -gt 10 ]; then
        echo "⚠️  HIGH FAILURE RATE!"
    fi
    
    sleep 300  # 5 minutos
done
```

## 📱 Integração com Ferramentas

### Slack Webhook

```python
import httpx

async def send_audit_alert_to_slack(message: str):
    """Envia alerta de auditoria para Slack."""
    
    webhook_url = "https://hooks.slack.com/services/YOUR/WEBHOOK/URL"
    
    payload = {
        "text": f"🔐 Audit Alert",
        "blocks": [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": message
                }
            }
        ]
    }
    
    async with httpx.AsyncClient() as client:
        await client.post(webhook_url, json=payload)

# Uso
await send_audit_alert_to_slack(
    "⚠️ *Integrity Violation Detected*\n"
    "2 audit logs failed integrity verification\n"
    "Project: Production\n"
    "Time: 2024-11-20 10:00:00"
)
```

### Grafana Dashboard

Exemplo de query para Grafana com PostgreSQL datasource:

```sql
-- Total operations per hour
SELECT 
    date_trunc('hour', timestamp) as time,
    COUNT(*) as operations
FROM akm_audit_logs
WHERE timestamp > NOW() - INTERVAL '24 hours'
GROUP BY time
ORDER BY time;

-- Success rate
SELECT 
    date_trunc('hour', timestamp) as time,
    COUNT(*) FILTER (WHERE status = 'success') * 100.0 / COUNT(*) as success_rate
FROM akm_audit_logs
WHERE timestamp > NOW() - INTERVAL '24 hours'
GROUP BY time;

-- Failed operations by type
SELECT 
    operation,
    COUNT(*) as count
FROM akm_audit_logs
WHERE status IN ('failure', 'denied')
  AND timestamp > NOW() - INTERVAL '24 hours'
GROUP BY operation
ORDER BY count DESC;
```

## ✅ Checklist de Verificação

Antes de ir para produção:

- [ ] Migration executada (`alembic upgrade head`)
- [ ] Scopes de auditoria importados
- [ ] API Key com `akm:audit:read` criada
- [ ] Verificação de integridade testada
- [ ] Dashboard de monitoramento configurado
- [ ] Alertas de segurança configurados
- [ ] Política de retenção de logs definida
- [ ] Backup de logs configurado
- [ ] Documentação revisada
- [ ] Equipe treinada no uso da API

## 🎯 Próximos Passos

1. **Testar os endpoints** de auditoria
2. **Configurar monitoramento** automático
3. **Definir políticas** de retenção
4. **Criar dashboards** personalizados
5. **Integrar com ferramentas** existentes

Para mais detalhes, consulte: [`AUDIT_SYSTEM.md`](AUDIT_SYSTEM.md)
