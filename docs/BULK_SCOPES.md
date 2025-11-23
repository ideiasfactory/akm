# Bulk Scopes Management

Sistema de gerenciamento em lote (bulk) de escopos com validação via JSON Schema.

## 📋 Estrutura de Arquivos

```
data/
  ├── scopes.json          # Definição completa dos escopos do sistema
  └── scopes_schema.json   # JSON Schema para validação

scripts/
  └── import_scopes.py     # Script CLI para importação em lote

src/api/
  ├── models/bulk_scopes.py    # Modelos Pydantic para validação
  └── routes/scopes.py         # Endpoints de bulk import/export
```

## 🔧 JSON Schema

O arquivo `data/scopes_schema.json` define a estrutura válida para arquivos de escopos:

### Propriedades Obrigatórias:
- **version**: Versão do schema (formato: `X.Y.Z`)
- **scopes**: Array de objetos scope

### Estrutura de cada Scope:
- **scope_name** (obrigatório): Nome único no formato `namespace:resource:action`
  - Padrão regex: `^[a-z0-9]+:[a-z0-9_]+:[a-z0-9_*]+$`
  - Exemplo: `akm:projects:read`, `akm:keys:*`
  
- **description** (obrigatório): Descrição legível
  - Min: 1 caractere, Max: 500 caracteres
  
- **category** (obrigatório): Categoria do escopo
  - Valores permitidos: `projects`, `keys`, `scopes`, `webhooks`, `alerts`, `usage`, `admin`, `system`
  
- **is_active** (opcional): Status do escopo
  - Padrão: `true`

## 📝 Arquivo de Escopos (scopes.json)

Exemplo de estrutura:

```json
{
  "version": "1.0.0",
  "scopes": [
    {
      "scope_name": "akm:projects:read",
      "description": "View projects and their details",
      "category": "projects",
      "is_active": true
    },
    {
      "scope_name": "akm:projects:write",
      "description": "Create and update projects",
      "category": "projects",
      "is_active": true
    }
  ]
}
```

## 🚀 Formas de Importação

### 1. Via Script CLI (Recomendado)

```bash
# Importar scopes do arquivo
python scripts/import_scopes.py data/scopes.json

# Dry run (validar sem importar)
python scripts/import_scopes.py data/scopes.json --dry-run
```

**Saída exemplo:**
```
================================================================================
Scopes Bulk Import
================================================================================

📄 Reading file: data\scopes.json
✅ JSON file parsed successfully
✅ Schema validation passed: 28 scopes found

📥 Importing scopes...

================================================================================
Import Results
================================================================================
✅ Total Processed: 28
✅ Created: 15
✅ Updated: 10
⏭️  Skipped: 3 (no changes)

📝 Processed scopes:
  - akm:projects:read
  - akm:projects:write
  - akm:keys:*
  ...
================================================================================
```

### 2. Via API - JSON Direto

```bash
curl -X POST http://localhost:8000/akm/scopes/bulk \
  -H "X-API-Key: $ADMIN_API_KEY" \
  -H "Content-Type: application/json" \
  -d @data/scopes.json
```

### 3. Via API - Upload de Arquivo

```bash
curl -X POST http://localhost:8000/akm/scopes/bulk/file \
  -H "X-API-Key: $ADMIN_API_KEY" \
  -F "file=@data/scopes.json"
```

## 📤 Exportação

### Via API

```bash
# Exportar todos os escopos ativos
curl -X GET http://localhost:8000/akm/scopes/export/json \
  -H "X-API-Key: $ADMIN_API_KEY" \
  > scopes_backup.json

# Exportar incluindo inativos
curl -X GET "http://localhost:8000/akm/scopes/export/json?active_only=false" \
  -H "X-API-Key: $ADMIN_API_KEY" \
  > scopes_all.json
```

## 🔄 Operação de Upsert

O bulk import usa a estratégia **upsert** (update or insert):

1. **Scope NÃO existe** → Cria novo scope
2. **Scope existe + dados diferentes** → Atualiza scope
3. **Scope existe + dados iguais** → Skipped (sem mudanças)

### Critério de Identificação:
- **scope_name** é usado como chave única
- Case-sensitive

### Campos Atualizados:
- `description`
- `is_active`

**Nota:** A categoria não é armazenada no banco, serve apenas para organização no arquivo JSON.

## ✅ Validação

A validação ocorre em múltiplas camadas:

### 1. JSON Schema (estrutura)
- Formato do arquivo
- Tipos de dados
- Campos obrigatórios

### 2. Pydantic Validators (regras de negócio)
- Formato do scope_name (regex)
- Categorias permitidas
- Versão semântica

### 3. Database Constraints
- Unique constraint em scope_name
- Foreign key validations

## 🔍 Casos de Uso

### 1. Setup Inicial
```bash
# Importar todos os escopos padrão
python scripts/import_scopes.py data/scopes.json
```

### 2. Adicionar Novos Escopos
Edite `data/scopes.json` e adicione:
```json
{
  "scope_name": "akm:billing:read",
  "description": "View billing information",
  "category": "admin",
  "is_active": true
}
```

Execute novamente:
```bash
python scripts/import_scopes.py data/scopes.json
```

### 3. Atualizar Descrições
Modifique descrições no JSON e reimporte - apenas os modificados serão atualizados.

### 4. Desativar Escopos
Mude `is_active` para `false` e reimporte:
```json
{
  "scope_name": "akm:deprecated:action",
  "description": "Deprecated scope",
  "category": "system",
  "is_active": false
}
```

### 5. Backup e Restore
```bash
# Backup
curl -X GET http://localhost:8000/akm/scopes/export/json \
  -H "X-API-Key: $ADMIN_API_KEY" \
  > backup_$(date +%Y%m%d).json

# Restore
python scripts/import_scopes.py backup_20251120.json
```

## 📊 Response Format

```json
{
  "total_processed": 28,
  "created": 15,
  "updated": 10,
  "skipped": 3,
  "errors": [],
  "scope_names": [
    "akm:projects:read",
    "akm:projects:write",
    "akm:keys:*"
  ]
}
```

## ⚠️ Erros Comuns

### 1. Formato de scope_name inválido
```
Error: Invalid scope name format: 'invalid-scope'. 
Expected format: 'namespace:resource:action'
```

**Solução:** Use o formato correto: `akm:resource:action`

### 2. Categoria inválida
```
Error: Invalid category: 'invalid'. 
Allowed values: projects, keys, scopes, webhooks, alerts, usage, admin, system
```

**Solução:** Use uma das categorias permitidas.

### 3. Versão inválida
```
Error: String should match pattern '^\d+\.\d+\.\d+$'
```

**Solução:** Use formato semântico: `1.0.0`

### 4. JSON inválido
```
Error: Invalid JSON format: Expecting ',' delimiter
```

**Solução:** Valide o JSON com um linter ou use `jq`:
```bash
cat data/scopes.json | jq .
```

## 🛠️ Desenvolvimento

### Adicionar Nova Categoria

1. Atualizar `data/scopes_schema.json`:
```json
"enum": [
  "projects", "keys", "scopes", "webhooks", 
  "alerts", "usage", "admin", "system",
  "nova_categoria"  // Adicionar aqui
]
```

2. Atualizar validador em `src/api/models/bulk_scopes.py`:
```python
allowed = ['projects', 'keys', 'scopes', 'webhooks', 
           'alerts', 'usage', 'admin', 'system', 'nova_categoria']
```

### Adicionar Novo Campo

1. Adicionar no schema JSON
2. Atualizar `BulkScopeItem` Pydantic model
3. Atualizar `bulk_upsert` no repository
4. Atualizar migration se necessário

## 📖 Referências

- **JSON Schema Spec:** https://json-schema.org/
- **Pydantic Validation:** https://docs.pydantic.dev/
- **FastAPI File Uploads:** https://fastapi.tiangolo.com/tutorial/request-files/

## 🔐 Permissões Necessárias

Todos os endpoints de bulk operations requerem:
- **Escopo:** `akm:scopes:write`
- **Alternativamente:** `akm:scopes:*` ou `akm:*`

## 💡 Dicas

1. **Use dry-run** antes de importar em produção
2. **Faça backup** antes de bulk updates
3. **Valide JSON** localmente antes de enviar
4. **Use versioning** no arquivo JSON
5. **Documente mudanças** nos commits

## 📝 Exemplo Completo

```bash
# 1. Validar arquivo
python scripts/import_scopes.py data/scopes.json --dry-run

# 2. Fazer backup atual
curl -X GET http://localhost:8000/akm/scopes/export/json \
  -H "X-API-Key: $ADMIN_API_KEY" \
  > backup_before_import.json

# 3. Importar
python scripts/import_scopes.py data/scopes.json

# 4. Verificar no banco
curl -X GET http://localhost:8000/akm/scopes \
  -H "X-API-Key: $ADMIN_API_KEY" | jq .
```
