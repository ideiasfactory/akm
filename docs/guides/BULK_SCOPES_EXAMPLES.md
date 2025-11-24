# Bulk Scopes Import - Exemplo Prático

Este guia mostra passo a passo como usar o sistema de importação em lote de escopos.

## 🎯 Cenário: Adicionar Novo Módulo de Billing

Vamos adicionar escopos para um novo módulo de billing ao sistema.

### Passo 1: Criar arquivo com novos escopos

Crie `data/billing_scopes.json`:

```json
{
  "version": "1.0.0",
  "scopes": [
    {
      "scope_name": "akm:billing:read",
      "description": "View billing information and invoices",
      "category": "admin",
      "is_active": true
    },
    {
      "scope_name": "akm:billing:write",
      "description": "Create and update billing information",
      "category": "admin",
      "is_active": true
    },
    {
      "scope_name": "akm:billing:delete",
      "description": "Delete billing records",
      "category": "admin",
      "is_active": true
    },
    {
      "scope_name": "akm:billing:*",
      "description": "Full billing access",
      "category": "admin",
      "is_active": true
    }
  ]
}
```

### Passo 2: Validar arquivo (dry-run)

```bash
python scripts/import_scopes.py data/billing_scopes.json --dry-run
```

**Saída esperada:**
```
================================================================================
Scopes Bulk Import
================================================================================

📄 Reading file: data\billing_scopes.json
✅ JSON file parsed successfully
✅ Schema validation passed: 4 scopes found

🔍 DRY RUN MODE - No changes will be made

Would import 4 scopes:
  - akm:billing:read: View billing information and invoices
  - akm:billing:write: Create and update billing information
  - akm:billing:delete: Delete billing records
  - akm:billing:*: Full billing access
```

### Passo 3: Importar

```bash
python scripts/import_scopes.py data/billing_scopes.json
```

**Saída esperada:**
```
================================================================================
Scopes Bulk Import
================================================================================

📄 Reading file: data\billing_scopes.json
✅ JSON file parsed successfully
✅ Schema validation passed: 4 scopes found

📥 Importing scopes...

================================================================================
Import Results
================================================================================
✅ Total Processed: 4
✅ Created: 4
✅ Updated: 0
⏭️  Skipped: 0 (no changes)

📝 Processed scopes:
  - akm:billing:read
  - akm:billing:write
  - akm:billing:delete
  - akm:billing:*
================================================================================
```

### Passo 4: Verificar no banco

```bash
curl -X GET "http://localhost:8000/akm/scopes?active_only=true" \
  -H "X-API-Key: $ADMIN_API_KEY" | jq '.[] | select(.scope_name | startswith("akm:billing"))'
```

**Resposta:**
```json
[
  {
    "scope_name": "akm:billing:read",
    "description": "View billing information and invoices",
    "is_active": true,
    "created_at": "2025-11-20T10:30:00Z"
  },
  {
    "scope_name": "akm:billing:write",
    "description": "Create and update billing information",
    "is_active": true,
    "created_at": "2025-11-20T10:30:00Z"
  }
  // ... outros 2 scopes
]
```

### Passo 5: Criar API key com novos escopos

```bash
curl -X POST http://localhost:8000/akm/keys \
  -H "X-API-Key: $ADMIN_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": 1,
    "name": "Billing Service Key",
    "description": "Key for billing microservice",
    "scope_names": ["akm:billing:*"],
    "expires_at": null
  }'
```

## 🔄 Cenário 2: Atualizar Descrições de Escopos Existentes

### Passo 1: Exportar escopos atuais

```bash
curl -X GET http://localhost:8000/akm/scopes/export/json \
  -H "X-API-Key: $ADMIN_API_KEY" \
  > data/scopes_current.json
```

### Passo 2: Editar descrições

Abra `data/scopes_current.json` e modifique as descrições:

```json
{
  "version": "1.0.0",
  "scopes": [
    {
      "scope_name": "akm:projects:read",
      "description": "View projects and their details (updated description)",  // MODIFICADO
      "category": "projects",
      "is_active": true
    }
    // ... outros scopes
  ]
}
```

### Passo 3: Reimportar

```bash
python scripts/import_scopes.py data/scopes_current.json
```

**Saída esperada:**
```
================================================================================
Import Results
================================================================================
✅ Total Processed: 28
✅ Created: 0
✅ Updated: 1      # Apenas o modificado
⏭️  Skipped: 27    # Os demais sem mudanças

📝 Processed scopes:
  - akm:projects:read  # Apenas o atualizado aparece
================================================================================
```

## 🔴 Cenário 3: Desativar Escopos Deprecados

### Passo 1: Modificar arquivo

```json
{
  "version": "1.0.0",
  "scopes": [
    {
      "scope_name": "akm:old_feature:read",
      "description": "DEPRECATED - Old feature access",
      "category": "system",
      "is_active": false  // DESATIVADO
    }
  ]
}
```

### Passo 2: Importar

```bash
python scripts/import_scopes.py data/deprecated_scopes.json
```

**Resultado:** Scope será desativado mas permanece no banco (soft delete).

## 📊 Cenário 4: Via API (sem script)

### Upload de arquivo

```bash
curl -X POST http://localhost:8000/akm/scopes/bulk/file \
  -H "X-API-Key: $ADMIN_API_KEY" \
  -F "file=@data/billing_scopes.json"
```

**Resposta:**
```json
{
  "total_processed": 4,
  "created": 4,
  "updated": 0,
  "skipped": 0,
  "errors": [],
  "scope_names": [
    "akm:billing:read",
    "akm:billing:write",
    "akm:billing:delete",
    "akm:billing:*"
  ]
}
```

### JSON direto no body

```bash
curl -X POST http://localhost:8000/akm/scopes/bulk \
  -H "X-API-Key: $ADMIN_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "version": "1.0.0",
    "scopes": [
      {
        "scope_name": "akm:test:read",
        "description": "Test scope",
        "category": "system",
        "is_active": true
      }
    ]
  }'
```

## 🛡️ Cenário 5: Validação de Erros

### Exemplo: Formato inválido

```json
{
  "version": "1.0.0",
  "scopes": [
    {
      "scope_name": "invalid-format",  // ERRADO: usa hífen
      "description": "Test",
      "category": "system"
    }
  ]
}
```

**Resultado:**
```
❌ Schema validation failed:
  - scopes.0.scope_name: Invalid scope name format: 'invalid-format'. 
    Expected format: 'namespace:resource:action'
```

### Exemplo: Categoria inválida

```json
{
  "version": "1.0.0",
  "scopes": [
    {
      "scope_name": "akm:test:read",
      "description": "Test",
      "category": "invalid_category"  // ERRADO
    }
  ]
}
```

**Resultado:**
```
❌ Schema validation failed:
  - scopes.0.category: Invalid category: 'invalid_category'. 
    Allowed values: projects, keys, scopes, webhooks, alerts, usage, admin, system
```

## 🔄 Cenário 6: Backup e Restore Completo

### Backup antes de mudanças

```bash
# 1. Exportar estado atual
curl -X GET http://localhost:8000/akm/scopes/export/json \
  -H "X-API-Key: $ADMIN_API_KEY" \
  > backup_$(date +%Y%m%d_%H%M%S).json

# 2. Fazer mudanças
python scripts/import_scopes.py data/new_scopes.json

# 3. Se algo der errado, restaurar backup
python scripts/import_scopes.py backup_20251120_103000.json
```

## 📈 Cenário 7: Migração de Ambiente

### Dev → Staging → Production

```bash
# 1. Exportar de DEV
curl -X GET http://dev.api.com/akm/scopes/export/json \
  -H "X-API-Key: $DEV_KEY" \
  > scopes_dev.json

# 2. Validar
python scripts/import_scopes.py scopes_dev.json --dry-run

# 3. Importar em STAGING
curl -X POST http://staging.api.com/akm/scopes/bulk/file \
  -H "X-API-Key: $STAGING_KEY" \
  -F "file=@scopes_dev.json"

# 4. Testar em STAGING
# ... testes ...

# 5. Importar em PRODUCTION
curl -X POST http://prod.api.com/akm/scopes/bulk/file \
  -H "X-API-Key: $PROD_KEY" \
  -F "file=@scopes_dev.json"
```

## 🧪 Cenário 8: CI/CD Integration

### GitHub Actions example

```yaml
name: Update Scopes

on:
  push:
    paths:
      - 'data/scopes.json'
    branches:
      - main

jobs:
  update-scopes:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      
      - name: Setup Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.12'
      
      - name: Install dependencies
        run: pip install -r requirements.txt
      
      - name: Validate scopes file
        run: python scripts/import_scopes.py data/scopes.json --dry-run
      
      - name: Import to staging
        run: |
          curl -X POST ${{ secrets.STAGING_API_URL }}/akm/scopes/bulk/file \
            -H "X-API-Key: ${{ secrets.STAGING_API_KEY }}" \
            -F "file=@data/scopes.json"
```

## 💡 Dicas Importantes

### ✅ DO:
- Sempre use `--dry-run` primeiro
- Faça backup antes de mudanças grandes
- Use versionamento no campo `version`
- Documente mudanças no git commit
- Valide JSON localmente: `cat scopes.json | jq .`

### ❌ DON'T:
- Não delete `scope_name` de escopos em uso
- Não mude `scope_name` (crie novo scope se necessário)
- Não use espaços ou caracteres especiais em `scope_name`
- Não remova escopos do arquivo (use `is_active: false`)

## 🎓 Resumo dos Comandos

```bash
# Validação local
python scripts/import_scopes.py file.json --dry-run

# Importação via script
python scripts/import_scopes.py file.json

# Importação via API (upload)
curl -X POST http://localhost:8000/akm/scopes/bulk/file \
  -H "X-API-Key: $KEY" -F "file=@file.json"

# Importação via API (JSON body)
curl -X POST http://localhost:8000/akm/scopes/bulk \
  -H "X-API-Key: $KEY" -H "Content-Type: application/json" \
  -d @file.json

# Exportação
curl -X GET http://localhost:8000/akm/scopes/export/json \
  -H "X-API-Key: $KEY" > export.json

# Listar scopes
curl -X GET http://localhost:8000/akm/scopes \
  -H "X-API-Key: $KEY"
```
