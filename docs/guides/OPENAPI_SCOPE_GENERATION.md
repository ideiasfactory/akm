# OpenAPI Scope Generation

Sistema automático de geração de escopos a partir de especificações OpenAPI/Swagger.

## 🎯 Visão Geral

Este sistema permite gerar automaticamente uma estrutura completa de escopos de permissão analisando especificações OpenAPI (Swagger). Isso é especialmente útil quando você está integrando uma API externa ou documentando permissões para sua própria API.

## 📋 Formatos Suportados

### Fontes de Entrada
- **URL**: Buscar spec de uma URL pública
- **File Upload**: Enviar arquivo JSON ou YAML
- **JSON Direct**: Fornecer spec diretamente no body

### Formatos de Arquivo
- OpenAPI 3.0.x (JSON/YAML)
- Swagger 2.0 (JSON/YAML)

## 🔧 Estratégias de Geração

### 1. **PATH_RESOURCE** (Recomendado)
Agrupa endpoints por recurso e gera escopos CRUD.

**Exemplo:**
```
GET    /api/users      → api:users:read
POST   /api/users      → api:users:write
PUT    /api/users/{id} → api:users:write
DELETE /api/users/{id} → api:users:delete
                        → api:users:* (wildcard)
```

**Quando usar:** APIs RESTful com recursos bem definidos.

### 2. **PATH_METHOD**
Um escopo por combinação de path + método HTTP.

**Exemplo:**
```
GET    /api/users      → api:users_get:read
POST   /api/users      → api:users_post:write
GET    /api/users/{id} → api:users_get:read
```

**Quando usar:** Controle granular por endpoint específico.

### 3. **TAG_BASED**
Usa as tags do OpenAPI para agrupar operações.

**Exemplo (tags: ["Users", "Admin"]):**
```
GET    /api/users  [tag: Users] → api:users:read
POST   /api/admin  [tag: Admin] → api:admin:write
                                 → api:users:* (wildcard)
                                 → api:admin:* (wildcard)
```

**Quando usar:** API bem organizada com tags significativas.

### 4. **OPERATION_ID**
Um escopo por operationId definido na spec.

**Exemplo:**
```
operationId: getUsers    → api:getUsers:execute
operationId: createUser  → api:createUser:execute
```

**Quando usar:** operationIds bem definidos e únicos.

## 🚀 Endpoints

### 1. Analisar Spec (Preview)

```http
POST /akm/scopes/openapi/analyze
```

Analisa a spec e retorna estatísticas **sem gerar** os escopos.

**Request:**
```json
{
  "source_type": "url",
  "source": "https://petstore3.swagger.io/api/v3/openapi.json"
}
```

**Response:**
```json
{
  "api_title": "Swagger Petstore",
  "api_version": "1.0.0",
  "total_paths": 13,
  "total_operations": 19,
  "http_methods": ["DELETE", "GET", "POST", "PUT"],
  "tags": ["pet", "store", "user"],
  "estimated_scopes_by_strategy": {
    "path_method": 19,
    "path_resource": 12,
    "tag_based": 12,
    "operation_id": 19
  },
  "sample_scopes": {
    "path_resource": [
      "api:pet:read",
      "api:pet:write",
      "api:store:read",
      "api:user:read",
      "api:user:write"
    ]
  }
}
```

### 2. Gerar Escopos

```http
POST /akm/scopes/openapi/generate
```

Gera escopos completos com descrições.

**Request:**
```json
{
  "source_type": "url",
  "source": "https://api.example.com/openapi.json",
  "strategy": "path_resource",
  "naming_config": {
    "namespace": "api",
    "include_version": false,
    "action_mapping": {
      "GET": "read",
      "POST": "write",
      "PUT": "write",
      "PATCH": "write",
      "DELETE": "delete"
    }
  },
  "category": "api",
  "generate_wildcards": true
}
```

**Response:**
```json
{
  "api_title": "My API",
  "api_version": "1.0.0",
  "total_scopes": 15,
  "strategy_used": "path_resource",
  "scopes": [
    {
      "scope_name": "api:users:read",
      "description": "Read operations for users (GET)",
      "category": "api",
      "is_active": true,
      "metadata": {
        "resource": "users",
        "action": "read",
        "methods": ["GET"],
        "paths": ["/api/users", "/api/users/{id}"]
      }
    },
    {
      "scope_name": "api:users:write",
      "description": "Write operations for users (POST, PUT)",
      "category": "api",
      "is_active": true,
      "metadata": {
        "resource": "users",
        "action": "write",
        "methods": ["POST", "PUT"],
        "paths": ["/api/users", "/api/users/{id}"]
      }
    },
    {
      "scope_name": "api:users:*",
      "description": "Full access to users resource",
      "category": "api",
      "is_active": true,
      "metadata": {
        "resource": "users",
        "wildcard": true
      }
    }
  ],
  "warnings": []
}
```

### 3. Gerar de URL (Simplificado)

```http
POST /akm/scopes/openapi/generate/url?url={url}&strategy={strategy}
```

**Exemplo:**
```bash
curl -X POST "http://localhost:8000/akm/scopes/openapi/generate/url?url=https://petstore3.swagger.io/api/v3/openapi.json&strategy=path_resource&namespace=petstore" \
  -H "X-API-Key: $ADMIN_API_KEY"
```

### 4. Gerar de Arquivo

```http
POST /akm/scopes/openapi/generate/file
```

**Exemplo:**
```bash
curl -X POST http://localhost:8000/akm/scopes/openapi/generate/file \
  -H "X-API-Key: $ADMIN_API_KEY" \
  -F "file=@openapi.json" \
  -F "strategy=path_resource" \
  -F "namespace=myapi"
```

### 5. Gerar e Importar (Tudo em Um)

```http
POST /akm/scopes/openapi/generate-and-import
```

Gera escopos e importa diretamente no banco.

**Request:**
```json
{
  "source_type": "url",
  "source": "https://api.example.com/openapi.json",
  "strategy": "path_resource",
  "naming_config": {
    "namespace": "myapi"
  },
  "category": "api",
  "generate_wildcards": true,
  "import_to_db": true
}
```

**Response:**
```json
{
  "total_processed": 15,
  "created": 12,
  "updated": 3,
  "skipped": 0,
  "errors": [],
  "scope_names": [
    "myapi:users:read",
    "myapi:users:write",
    "myapi:users:delete",
    "myapi:users:*"
  ]
}
```

## 💡 Exemplos de Uso

### Exemplo 1: Análise Prévia

```bash
# 1. Analisar spec primeiro
curl -X POST http://localhost:8000/akm/scopes/openapi/analyze \
  -H "X-API-Key: $ADMIN_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "source_type": "url",
    "source": "https://petstore3.swagger.io/api/v3/openapi.json"
  }' | jq .

# Output mostra quantos scopes cada estratégia geraria
```

### Exemplo 2: Gerar de URL Pública

```bash
# Gerar escopos do Petstore Swagger
curl -X POST "http://localhost:8000/akm/scopes/openapi/generate/url?url=https://petstore3.swagger.io/api/v3/openapi.json&namespace=petstore&strategy=path_resource" \
  -H "X-API-Key: $ADMIN_API_KEY" | jq . > petstore_scopes.json
```

### Exemplo 3: Gerar de Arquivo Local

```bash
# 1. Baixar spec
curl https://api.example.com/openapi.json > myapi_openapi.json

# 2. Gerar escopos
curl -X POST http://localhost:8000/akm/scopes/openapi/generate/file \
  -H "X-API-Key: $ADMIN_API_KEY" \
  -F "file=@myapi_openapi.json" \
  -F "strategy=path_resource" \
  -F "namespace=myapi" \
  | jq . > myapi_scopes.json
```

### Exemplo 4: Gerar e Importar Direto

```bash
curl -X POST http://localhost:8000/akm/scopes/openapi/generate-and-import \
  -H "X-API-Key: $ADMIN_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "source_type": "url",
    "source": "https://api.example.com/openapi.json",
    "strategy": "path_resource",
    "naming_config": {
      "namespace": "myapi",
      "include_version": false
    },
    "category": "api",
    "generate_wildcards": true
  }'
```

### Exemplo 5: Comparar Estratégias

```bash
# Função helper
analyze_strategy() {
  curl -X POST http://localhost:8000/akm/scopes/openapi/generate \
    -H "X-API-Key: $ADMIN_API_KEY" \
    -H "Content-Type: application/json" \
    -d "{
      \"source_type\": \"url\",
      \"source\": \"$1\",
      \"strategy\": \"$2\",
      \"naming_config\": {\"namespace\": \"api\"}
    }" | jq '.total_scopes, .scopes[0:3]'
}

# Comparar
analyze_strategy "https://petstore3.swagger.io/api/v3/openapi.json" "path_resource"
analyze_strategy "https://petstore3.swagger.io/api/v3/openapi.json" "tag_based"
analyze_strategy "https://petstore3.swagger.io/api/v3/openapi.json" "operation_id"
```

## 🔄 Workflow Completo

### Setup de API Externa

```bash
#!/bin/bash

API_URL="https://api.github.com/openapi.json"
NAMESPACE="github"

# 1. Analisar
echo "=== Analyzing API ==="
curl -X POST http://localhost:8000/akm/scopes/openapi/analyze \
  -H "X-API-Key: $ADMIN_API_KEY" \
  -H "Content-Type: application/json" \
  -d "{\"source_type\": \"url\", \"source\": \"$API_URL\"}" \
  | jq '.estimated_scopes_by_strategy'

# 2. Gerar preview
echo "=== Generating Preview ==="
curl -X POST http://localhost:8000/akm/scopes/openapi/generate \
  -H "X-API-Key: $ADMIN_API_KEY" \
  -H "Content-Type: application/json" \
  -d "{
    \"source_type\": \"url\",
    \"source\": \"$API_URL\",
    \"strategy\": \"path_resource\",
    \"naming_config\": {\"namespace\": \"$NAMESPACE\"}
  }" | jq '.total_scopes, .scopes[0:5]'

# 3. Confirmar e importar
read -p "Import to database? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
  curl -X POST http://localhost:8000/akm/scopes/openapi/generate-and-import \
    -H "X-API-Key: $ADMIN_API_KEY" \
    -H "Content-Type: application/json" \
    -d "{
      \"source_type\": \"url\",
      \"source\": \"$API_URL\",
      \"strategy\": \"path_resource\",
      \"naming_config\": {\"namespace\": \"$NAMESPACE\"},
      \"category\": \"external_api\"
    }" | jq .
fi
```

## ⚙️ Configuração Avançada

### Custom Action Mapping

```json
{
  "naming_config": {
    "namespace": "api",
    "action_mapping": {
      "GET": "view",
      "POST": "create",
      "PUT": "update",
      "PATCH": "modify",
      "DELETE": "remove",
      "HEAD": "check",
      "OPTIONS": "discover"
    }
  }
}
```

Resultado:
```
GET    /users → api:users:view
POST   /users → api:users:create
PUT    /users → api:users:update
DELETE /users → api:users:remove
```

### Include API Version

```json
{
  "naming_config": {
    "namespace": "api",
    "include_version": true
  }
}
```

Resultado:
```
api:v1:users:read
api:v1:users:write
```

### Sem Wildcards

```json
{
  "generate_wildcards": false
}
```

Não gera escopos com `*` (útil para controle mais restrito).

## 📊 Metadata Gerada

Cada escopo gerado inclui metadata útil:

```json
{
  "scope_name": "api:users:read",
  "metadata": {
    "resource": "users",
    "action": "read",
    "methods": ["GET"],
    "paths": ["/api/users", "/api/users/{id}"],
    "tags": ["Users", "Account"]
  }
}
```

Útil para:
- Documentação automática
- Auditoria
- Debugging

## 🎨 Estratégias por Caso de Uso

| Caso de Uso | Estratégia Recomendada | Motivo |
|-------------|------------------------|--------|
| API REST padrão | `path_resource` | CRUD natural, wildcards úteis |
| Microserviços | `tag_based` | Agrupa por serviço/módulo |
| API GraphQL-like | `operation_id` | Operações nomeadas |
| Controle fino | `path_method` | Máxima granularidade |
| API pública | `path_resource` | Fácil entendimento |
| API interna | `tag_based` | Alinha com arquitetura |

## ⚠️ Limitações

1. **operationId obrigatório**: Estratégia `operation_id` requer operationIds únicos
2. **Tags vazias**: Operações sem tags vão para categoria "untagged"
3. **Path parameters**: `{id}`, `{uuid}` são removidos do nome do escopo
4. **Descrições longas**: Limitadas a 500 caracteres
5. **Specs inválidas**: Requer OpenAPI/Swagger válidos

## 🔐 Permissões

| Endpoint | Scope Necessário |
|----------|------------------|
| `/analyze` | `akm:scopes:read` |
| `/generate` | `akm:scopes:read` |
| `/generate/file` | `akm:scopes:read` |
| `/generate/url` | `akm:scopes:read` |
| `/generate-and-import` | `akm:scopes:write` |

## 💡 Tips & Tricks

### 1. Preview Antes de Importar

Sempre use `/analyze` ou `/generate` antes de importar:
```bash
# Preview
curl ... /generate | jq '.total_scopes'

# Se OK, importar
curl ... /generate-and-import
```

### 2. Exportar para Bulk Import

Gere o JSON e use com bulk import:
```bash
curl ... /generate | jq '.scopes' > external_api_scopes.json

# Converter para formato bulk
jq '{version: "1.0.0", scopes: .}' external_api_scopes.json \
  | curl -X POST .../scopes/bulk -d @-
```

### 3. Versionar Specs

Mantenha versões das specs para regenerar:
```bash
mkdir -p specs/
curl $API_URL > specs/api_v1.0.0.json
```

### 4. CI/CD Integration

```yaml
- name: Generate API Scopes
  run: |
    curl -X POST $API/scopes/openapi/generate-and-import \
      -H "X-API-Key: ${{ secrets.API_KEY }}" \
      -d @openapi.json
```

## 📚 Referências

- [OpenAPI Specification](https://swagger.io/specification/)
- [Swagger Editor](https://editor.swagger.io/)
- [Petstore Example](https://petstore3.swagger.io/)
