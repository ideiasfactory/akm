# OpenAPI Scope Generation - Exemplos Práticos

Exemplos reais de geração de escopos a partir de APIs públicas conhecidas.

## 📚 Exemplo 1: Swagger Petstore

API de exemplo oficial do Swagger.

### Análise

```bash
curl -X POST http://localhost:8000/akm/scopes/openapi/analyze \
  -H "X-API-Key: $ADMIN_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "source_type": "url",
    "source": "https://petstore3.swagger.io/api/v3/openapi.json"
  }'
```

**Resultado:**
```json
{
  "api_title": "Swagger Petstore - OpenAPI 3.0",
  "api_version": "1.0.11",
  "total_paths": 13,
  "total_operations": 19,
  "http_methods": ["DELETE", "GET", "POST", "PUT"],
  "tags": ["pet", "store", "user"],
  "estimated_scopes_by_strategy": {
    "path_method": 19,
    "path_resource": 15,
    "tag_based": 12,
    "operation_id": 19
  }
}
```

### Gerar com Estratégia PATH_RESOURCE

```bash
curl -X POST http://localhost:8000/akm/scopes/openapi/generate/url \
  -H "X-API-Key: $ADMIN_API_KEY" \
  -d "url=https://petstore3.swagger.io/api/v3/openapi.json" \
  -d "strategy=path_resource" \
  -d "namespace=petstore" \
  -d "category=external_api" | jq '.scopes[] | {scope_name, description}'
```

**Escopos Gerados:**
```json
[
  {
    "scope_name": "petstore:pet:read",
    "description": "Read operations for pet (GET)"
  },
  {
    "scope_name": "petstore:pet:write",
    "description": "Write operations for pet (POST, PUT)"
  },
  {
    "scope_name": "petstore:pet:delete",
    "description": "Delete operations for pet (DELETE)"
  },
  {
    "scope_name": "petstore:pet:*",
    "description": "Full access to pet resource"
  },
  {
    "scope_name": "petstore:store:read",
    "description": "Read operations for store (GET)"
  },
  {
    "scope_name": "petstore:store:write",
    "description": "Write operations for store (POST)"
  },
  {
    "scope_name": "petstore:store:delete",
    "description": "Delete operations for store (DELETE)"
  },
  {
    "scope_name": "petstore:store:*",
    "description": "Full access to store resource"
  },
  {
    "scope_name": "petstore:user:read",
    "description": "Read operations for user (GET)"
  },
  {
    "scope_name": "petstore:user:write",
    "description": "Write operations for user (POST, PUT)"
  },
  {
    "scope_name": "petstore:user:delete",
    "description": "Delete operations for user (DELETE)"
  },
  {
    "scope_name": "petstore:user:*",
    "description": "Full access to user resource"
  }
]
```

### Importar para Banco

```bash
curl -X POST http://localhost:8000/akm/scopes/openapi/generate-and-import \
  -H "X-API-Key: $ADMIN_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "source_type": "url",
    "source": "https://petstore3.swagger.io/api/v3/openapi.json",
    "strategy": "path_resource",
    "naming_config": {
      "namespace": "petstore"
    },
    "category": "external_api",
    "generate_wildcards": true
  }'
```

**Resultado:**
```json
{
  "total_processed": 12,
  "created": 12,
  "updated": 0,
  "skipped": 0,
  "errors": [],
  "scope_names": [
    "petstore:pet:read",
    "petstore:pet:write",
    "petstore:pet:delete",
    "petstore:pet:*",
    "petstore:store:read",
    "petstore:store:write",
    "petstore:store:delete",
    "petstore:store:*",
    "petstore:user:read",
    "petstore:user:write",
    "petstore:user:delete",
    "petstore:user:*"
  ]
}
```

## 🏢 Exemplo 2: API Interna (Mock)

Usando um arquivo OpenAPI local para API interna.

### Arquivo: `company_api_openapi.json`

```json
{
  "openapi": "3.0.0",
  "info": {
    "title": "Company Internal API",
    "version": "2.0.0"
  },
  "paths": {
    "/employees": {
      "get": {
        "tags": ["HR"],
        "operationId": "listEmployees",
        "summary": "List all employees"
      },
      "post": {
        "tags": ["HR"],
        "operationId": "createEmployee",
        "summary": "Create new employee"
      }
    },
    "/employees/{id}": {
      "get": {
        "tags": ["HR"],
        "operationId": "getEmployee",
        "summary": "Get employee by ID"
      },
      "put": {
        "tags": ["HR"],
        "operationId": "updateEmployee",
        "summary": "Update employee"
      },
      "delete": {
        "tags": ["HR"],
        "operationId": "deleteEmployee",
        "summary": "Delete employee"
      }
    },
    "/departments": {
      "get": {
        "tags": ["Organization"],
        "operationId": "listDepartments",
        "summary": "List all departments"
      },
      "post": {
        "tags": ["Organization"],
        "operationId": "createDepartment",
        "summary": "Create new department"
      }
    },
    "/payroll": {
      "get": {
        "tags": ["Finance"],
        "operationId": "getPayroll",
        "summary": "Get payroll data"
      },
      "post": {
        "tags": ["Finance"],
        "operationId": "processPayroll",
        "summary": "Process payroll"
      }
    }
  }
}
```

### Gerar com TAG_BASED

```bash
curl -X POST http://localhost:8000/akm/scopes/openapi/generate/file \
  -H "X-API-Key: $ADMIN_API_KEY" \
  -F "file=@company_api_openapi.json" \
  -F "strategy=tag_based" \
  -F "namespace=company" \
  -F "category=internal"
```

**Escopos Gerados:**
```json
{
  "total_scopes": 12,
  "scopes": [
    {
      "scope_name": "company:hr:read",
      "description": "Read operations for hr (GET)",
      "metadata": {"tag": "hr", "action": "read", "methods": ["GET"]}
    },
    {
      "scope_name": "company:hr:write",
      "description": "Write operations for hr (POST, PUT)",
      "metadata": {"tag": "hr", "action": "write", "methods": ["POST", "PUT"]}
    },
    {
      "scope_name": "company:hr:delete",
      "description": "Delete operations for hr (DELETE)",
      "metadata": {"tag": "hr", "action": "delete", "methods": ["DELETE"]}
    },
    {
      "scope_name": "company:hr:*",
      "description": "Full access to hr operations"
    },
    {
      "scope_name": "company:organization:read",
      "description": "Read operations for organization (GET)",
      "metadata": {"tag": "organization", "action": "read"}
    },
    {
      "scope_name": "company:organization:write",
      "description": "Write operations for organization (POST)",
      "metadata": {"tag": "organization", "action": "write"}
    },
    {
      "scope_name": "company:organization:*",
      "description": "Full access to organization operations"
    },
    {
      "scope_name": "company:finance:read",
      "description": "Read operations for finance (GET)",
      "metadata": {"tag": "finance", "action": "read"}
    },
    {
      "scope_name": "company:finance:write",
      "description": "Write operations for finance (POST)",
      "metadata": {"tag": "finance", "action": "write"}
    },
    {
      "scope_name": "company:finance:*",
      "description": "Full access to finance operations"
    }
  ]
}
```

### Criar API Key com Escopos Gerados

```bash
# 1. Importar escopos
curl -X POST http://localhost:8000/akm/scopes/openapi/generate-and-import \
  -H "X-API-Key: $ADMIN_API_KEY" \
  -F "file=@company_api_openapi.json" \
  -F "strategy=tag_based" \
  -F "namespace=company"

# 2. Criar API key para HR Manager (apenas HR)
curl -X POST http://localhost:8000/akm/keys \
  -H "X-API-Key: $ADMIN_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": 1,
    "name": "HR Manager Key",
    "scope_names": ["company:hr:*"],
    "expires_at": null
  }'

# 3. Criar API key para Finance (apenas Finance read)
curl -X POST http://localhost:8000/akm/keys \
  -H "X-API-Key: $ADMIN_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": 1,
    "name": "Finance Viewer Key",
    "scope_names": ["company:finance:read"],
    "expires_at": null
  }'
```

## 🔄 Exemplo 3: Comparação de Estratégias

Usando a mesma API com diferentes estratégias.

### Script de Comparação

```bash
#!/bin/bash

API_URL="https://petstore3.swagger.io/api/v3/openapi.json"

echo "=== PATH_RESOURCE Strategy ==="
curl -X POST http://localhost:8000/akm/scopes/openapi/generate \
  -H "X-API-Key: $ADMIN_API_KEY" \
  -H "Content-Type: application/json" \
  -d "{
    \"source_type\": \"url\",
    \"source\": \"$API_URL\",
    \"strategy\": \"path_resource\",
    \"naming_config\": {\"namespace\": \"pet\"},
    \"generate_wildcards\": false
  }" | jq '{total: .total_scopes, samples: [.scopes[0:3][].scope_name]}'

echo "=== TAG_BASED Strategy ==="
curl -X POST http://localhost:8000/akm/scopes/openapi/generate \
  -H "X-API-Key: $ADMIN_API_KEY" \
  -H "Content-Type: application/json" \
  -d "{
    \"source_type\": \"url\",
    \"source\": \"$API_URL\",
    \"strategy\": \"tag_based\",
    \"naming_config\": {\"namespace\": \"pet\"},
    \"generate_wildcards\": false
  }" | jq '{total: .total_scopes, samples: [.scopes[0:3][].scope_name]}'

echo "=== OPERATION_ID Strategy ==="
curl -X POST http://localhost:8000/akm/scopes/openapi/generate \
  -H "X-API-Key: $ADMIN_API_KEY" \
  -H "Content-Type: application/json" \
  -d "{
    \"source_type\": \"url\",
    \"source\": \"$API_URL\",
    \"strategy\": \"operation_id\",
    \"naming_config\": {\"namespace\": \"pet\"}
  }" | jq '{total: .total_scopes, samples: [.scopes[0:3][].scope_name]}'
```

**Output:**
```json
=== PATH_RESOURCE Strategy ===
{
  "total": 9,
  "samples": [
    "pet:pet:read",
    "pet:pet:write",
    "pet:pet:delete"
  ]
}

=== TAG_BASED Strategy ===
{
  "total": 9,
  "samples": [
    "pet:pet:read",
    "pet:pet:write",
    "pet:pet:delete"
  ]
}

=== OPERATION_ID Strategy ===
{
  "total": 19,
  "samples": [
    "pet:updatePet:execute",
    "pet:addPet:execute",
    "pet:findPetsByStatus:execute"
  ]
}
```

## 🎨 Exemplo 4: Custom Action Mapping

Mapeamento personalizado de ações HTTP.

```bash
curl -X POST http://localhost:8000/akm/scopes/openapi/generate \
  -H "X-API-Key: $ADMIN_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "source_type": "url",
    "source": "https://petstore3.swagger.io/api/v3/openapi.json",
    "strategy": "path_resource",
    "naming_config": {
      "namespace": "pet",
      "action_mapping": {
        "GET": "view",
        "POST": "create",
        "PUT": "update",
        "PATCH": "modify",
        "DELETE": "remove"
      }
    }
  }' | jq '.scopes[] | select(.metadata.resource == "pet") | .scope_name'
```

**Resultado:**
```
"pet:pet:view"
"pet:pet:create"
"pet:pet:update"
"pet:pet:remove"
"pet:pet:*"
```

## 🔗 Exemplo 5: Pipeline CI/CD

Automatizar geração de escopos em pipeline.

### GitHub Actions

```yaml
name: Update API Scopes

on:
  push:
    paths:
      - 'api/openapi.json'
    branches:
      - main

jobs:
  update-scopes:
    runs-on: ubuntu-latest
    
    steps:
      - name: Checkout
        uses: actions/checkout@v2
      
      - name: Analyze OpenAPI Spec
        id: analyze
        run: |
          ANALYSIS=$(curl -X POST ${{ secrets.AKM_API_URL }}/akm/scopes/openapi/analyze \
            -H "X-API-Key: ${{ secrets.AKM_API_KEY }}" \
            -H "Content-Type: application/json" \
            -d @api/openapi.json)
          
          echo "Total scopes: $(echo $ANALYSIS | jq .estimated_scopes_by_strategy.path_resource)"
      
      - name: Generate and Import Scopes
        run: |
          curl -X POST ${{ secrets.AKM_API_URL }}/akm/scopes/openapi/generate-and-import \
            -H "X-API-Key: ${{ secrets.AKM_API_KEY }}" \
            -H "Content-Type: application/json" \
            -d '{
              "source_type": "json",
              "spec_data": '$(<api/openapi.json)',
              "strategy": "path_resource",
              "naming_config": {"namespace": "myapi"},
              "category": "api"
            }' > scope_import_result.json
      
      - name: Report Results
        run: |
          cat scope_import_result.json | jq '{
            created: .created,
            updated: .updated,
            total: .total_processed
          }'
```

## 📦 Exemplo 6: Backup e Versionamento

Manter histórico de escopos gerados.

```bash
#!/bin/bash

API_URL="https://api.example.com/openapi.json"
NAMESPACE="myapi"
VERSION=$(curl -s $API_URL | jq -r '.info.version')
DATE=$(date +%Y%m%d)

# Diretório de backup
mkdir -p backups/$NAMESPACE

# Gerar escopos
curl -X POST http://localhost:8000/akm/scopes/openapi/generate \
  -H "X-API-Key: $ADMIN_API_KEY" \
  -H "Content-Type: application/json" \
  -d "{
    \"source_type\": \"url\",
    \"source\": \"$API_URL\",
    \"strategy\": \"path_resource\",
    \"naming_config\": {\"namespace\": \"$NAMESPACE\"}
  }" > "backups/$NAMESPACE/scopes_v${VERSION}_${DATE}.json"

# Converter para formato bulk import
jq '{
  version: .api_version,
  scopes: [.scopes[] | {
    scope_name,
    description,
    category,
    is_active
  }]
}' "backups/$NAMESPACE/scopes_v${VERSION}_${DATE}.json" \
  > "backups/$NAMESPACE/bulk_import_v${VERSION}_${DATE}.json"

echo "✅ Backup saved: backups/$NAMESPACE/scopes_v${VERSION}_${DATE}.json"

# Commit to git
git add backups/
git commit -m "chore: backup API scopes v$VERSION"
```

## 🧪 Exemplo 7: Testing Different Namespaces

```bash
# Desenvolvimento
curl ... -d '{"naming_config": {"namespace": "dev_api"}}'

# Staging
curl ... -d '{"naming_config": {"namespace": "stg_api"}}'

# Production
curl ... -d '{"naming_config": {"namespace": "api"}}'
```

Isso permite ter escopos separados por ambiente!

## 💡 Exemplo 8: Bulk Processing

Processar múltiplas APIs de uma vez.

```bash
#!/bin/bash

# Lista de APIs para processar
declare -a APIS=(
  "users:https://api.example.com/users/openapi.json"
  "products:https://api.example.com/products/openapi.json"
  "orders:https://api.example.com/orders/openapi.json"
)

for api in "${APIS[@]}"; do
  IFS=':' read -r namespace url <<< "$api"
  
  echo "Processing $namespace..."
  
  curl -X POST http://localhost:8000/akm/scopes/openapi/generate-and-import \
    -H "X-API-Key: $ADMIN_API_KEY" \
    -H "Content-Type: application/json" \
    -d "{
      \"source_type\": \"url\",
      \"source\": \"$url\",
      \"strategy\": \"path_resource\",
      \"naming_config\": {\"namespace\": \"$namespace\"},
      \"category\": \"microservices\"
    }" | jq '{namespace: "'$namespace'", created: .created, updated: .updated}'
  
  sleep 1
done
```

## 🎯 Resumo de Comandos

```bash
# Análise rápida
curl -X POST .../analyze -d '{"source_type":"url","source":"URL"}'

# Gerar de URL
curl -X POST ".../generate/url?url=URL&namespace=api"

# Gerar de arquivo
curl -X POST .../generate/file -F "file=@spec.json"

# Gerar e importar
curl -X POST .../generate-and-import -d @request.json

# Exportar para bulk
curl ... /generate | jq '.scopes' > scopes.json
```
