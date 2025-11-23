# Sensitive Fields - Global vs Project-Specific

## Arquitetura

O sistema de **Sensitive Fields** suporta dois níveis de configuração:

### 🌍 Campos Globais (Global Fields)
- `project_id = NULL`
- Aplicam-se a **TODOS os projetos** por padrão
- Definidos no seed inicial
- Exemplos: `password`, `token`, `secret`, `api_key`, `key_hash`, etc.

### 📁 Campos Específicos do Projeto (Project-Specific Fields)
- `project_id = <ID do projeto>`
- Aplicam-se **somente ao projeto específico**
- Podem **sobrescrever** campos globais ou **adicionar novos** campos
- Exemplos: `customer_ssn`, `account_number`, `internal_token`

## Constraint de Unicidade

```sql
UNIQUE (project_id, field_name)
```

Isso significa:
- ✅ Você pode ter `password` global (`project_id=NULL`)
- ✅ Você pode ter `password` para projeto 1 (`project_id=1`)
- ✅ Você pode ter `password` para projeto 2 (`project_id=2`)
- ❌ Você **não pode** ter dois `password` para o mesmo projeto

## Lógica de Aplicação

Quando o sistema processa requisições:

1. **Carrega campos globais** (`project_id IS NULL`)
2. **Carrega campos do projeto específico** (`project_id = X`)
3. **Merge**: Se o projeto define o mesmo campo, a configuração do projeto **sobrescreve** a global

### Exemplo de Query

```sql
-- Buscar todos os campos aplicáveis ao projeto 1
SELECT field_name, strategy, replacement, mask_char
FROM akm_sensitive_fields
WHERE (project_id IS NULL OR project_id = 1)
  AND is_active = true
ORDER BY 
  project_id NULLS LAST,  -- Campos do projeto têm precedência
  field_name;
```

## Casos de Uso

### Caso 1: Usar Apenas Campos Globais
**Cenário:** Projeto novo que usa os padrões

```sql
-- Não precisa fazer nada! Os campos globais já se aplicam
-- password, token, secret, etc. serão sanitizados automaticamente
```

### Caso 2: Adicionar Campos Específicos
**Cenário:** Projeto tem campos adicionais sensíveis

```sql
-- Adicionar campo específico do projeto 1
INSERT INTO akm_sensitive_fields 
(project_id, field_name, is_active, strategy, replacement)
VALUES 
(1, 'customer_ssn', true, 'mask', NULL),
(1, 'account_number', true, 'mask', NULL),
(1, 'internal_token', true, 'redact', '[INTERNAL]');
```

Resultado para projeto 1:
- 🌍 11 campos globais (password, token, etc.)
- 📁 3 campos específicos (customer_ssn, account_number, internal_token)
- **Total: 14 campos sanitizados**

### Caso 3: Sobrescrever Configuração Global
**Cenário:** Projeto quer mascarar `password` em vez de redact

```sql
-- Campo global: password com strategy='redact'
-- Sobrescrever para projeto 1:
INSERT INTO akm_sensitive_fields 
(project_id, field_name, is_active, strategy, mask_show_start, mask_show_end, mask_char)
VALUES 
(1, 'password', true, 'mask', 2, 2, '*');
```

Resultado:
- Outros projetos: `password` → `[REDACTED]`
- Projeto 1: `password` → `ab******xy` (masked)

### Caso 4: Desabilitar Campo Global para um Projeto
**Cenário:** Projeto não quer sanitizar `bearer` tokens

```sql
-- Criar campo específico com is_active=false
INSERT INTO akm_sensitive_fields 
(project_id, field_name, is_active, strategy)
VALUES 
(1, 'bearer', false, 'redact');
```

Resultado:
- Outros projetos: `bearer` sanitizado
- Projeto 1: `bearer` **não sanitizado** (is_active=false)

## Exemplo de Migration

```python
"""add_project_specific_sensitive_fields

Revision ID: xxxxxxxxxxxx
"""
from alembic import op
from sqlalchemy import text


def upgrade() -> None:
    conn = op.get_bind()
    
    # Adicionar campos específicos para projeto ID 2 (exemplo: e-commerce)
    project_fields = [
        (2, 'credit_card_number', 'mask', 4, 4, '*'),
        (2, 'cvv', 'redact', '[***]'),
        (2, 'customer_email', 'mask', 3, 0, '*'),
    ]
    
    for project_id, field_name, strategy, *params in project_fields:
        if strategy == 'mask':
            show_start, show_end, mask_char = params
            conn.execute(text("""
                INSERT INTO akm_sensitive_fields 
                (project_id, field_name, is_active, strategy, mask_show_start, mask_show_end, mask_char)
                VALUES (:pid, :fname, true, 'mask', :start, :end, :char)
            """), {
                "pid": project_id, 
                "fname": field_name,
                "start": show_start,
                "end": show_end,
                "char": mask_char
            })
        else:  # redact
            replacement = params[0]
            conn.execute(text("""
                INSERT INTO akm_sensitive_fields 
                (project_id, field_name, is_active, strategy, replacement)
                VALUES (:pid, :fname, true, 'redact', :repl)
            """), {
                "pid": project_id,
                "fname": field_name,
                "repl": replacement
            })


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(text("DELETE FROM akm_sensitive_fields WHERE project_id = 2"))
```

## API para Gerenciar Campos

### Listar Campos (Global + Projeto)

```python
# GET /api/v1/sensitive-fields?project_id=1

# Response:
{
  "global_fields": [
    {"field_name": "password", "strategy": "redact", "replacement": "[REDACTED]"},
    {"field_name": "token", "strategy": "redact", "replacement": "[REDACTED]"},
    ...
  ],
  "project_fields": [
    {"field_name": "customer_ssn", "strategy": "mask", "mask_show_start": 0, "mask_show_end": 4},
    {"field_name": "account_number", "strategy": "mask", "mask_show_start": 2, "mask_show_end": 2}
  ],
  "effective_fields": {
    "password": {"strategy": "redact", "source": "global"},
    "token": {"strategy": "redact", "source": "global"},
    "customer_ssn": {"strategy": "mask", "source": "project"},
    "account_number": {"strategy": "mask", "source": "project"}
  }
}
```

### Criar Campo Específico do Projeto

```python
# POST /api/v1/projects/1/sensitive-fields
{
  "field_name": "customer_ssn",
  "strategy": "mask",
  "mask_show_start": 0,
  "mask_show_end": 4,
  "mask_char": "*"
}
```

### Sobrescrever Campo Global

```python
# POST /api/v1/projects/1/sensitive-fields
{
  "field_name": "password",  # Já existe globalmente
  "strategy": "mask",
  "mask_show_start": 2,
  "mask_show_end": 2,
  "mask_char": "*"
}
# Resultado: projeto 1 usa mask, outros projetos usam redact
```

## Benefícios

✅ **Flexibilidade:** Cada projeto pode ter suas próprias regras  
✅ **Padrões Globais:** Novos projetos já vêm com proteção básica  
✅ **Customização:** Override fácil de campos globais  
✅ **Isolamento:** Mudanças em um projeto não afetam outros  
✅ **Auditoria:** Clara separação entre global vs. específico

## Verificação

```sql
-- Ver campos globais
SELECT * FROM akm_sensitive_fields WHERE project_id IS NULL;

-- Ver campos do projeto 1
SELECT * FROM akm_sensitive_fields WHERE project_id = 1;

-- Ver campos efetivos para projeto 1 (global + projeto)
SELECT 
  field_name,
  CASE WHEN project_id IS NULL THEN '🌍 Global' ELSE '📁 Project' END as source,
  strategy,
  replacement,
  mask_char
FROM akm_sensitive_fields
WHERE (project_id IS NULL OR project_id = 1)
  AND is_active = true
ORDER BY project_id NULLS LAST, field_name;
```

## Migração de Dados Existentes

Se você já tinha `akm_sensitive_fields` sem `project_id`:

```sql
-- ANTES da migration, todos os campos eram "globais implicitamente"
-- DEPOIS da migration, definir explicitamente como globais:

UPDATE akm_sensitive_fields 
SET project_id = NULL 
WHERE project_id IS NULL;  -- Garantir que são NULL

-- Ou migrar campos existentes para um projeto específico:
UPDATE akm_sensitive_fields 
SET project_id = 1 
WHERE field_name IN ('customer_ssn', 'account_number');
```
