# API Versioning Guide

## 📋 Overview

Este projeto implementa versionamento de API usando **prefixo de URL** (`/v1`, `/v2`, etc.), seguindo as melhores práticas da indústria.

## 🎯 Estrutura de URLs

### **Versionadas (Recomendado)**
```
GET  /akm/v1/keys
POST /akm/v1/keys
GET  /akm/v1/projects
```

### **Legacy (Deprecated)**
```
GET  /akm/keys       → Funciona mas deprecated
POST /akm/keys       → Funciona mas deprecated
GET  /akm/projects   → Funciona mas deprecated
```

**⚠️ As rotas legacy (sem versão) serão removidas em versões futuras!**

## 🏗️ Estrutura de Diretórios

```
src/api/
  ├── versioning.py          # Utilitários de versionamento
  ├── routes/                # Rotas originais (compartilhadas)
  │   ├── keys.py
  │   ├── projects.py
  │   └── ...
  ├── v1/
  │   ├── __init__.py        # v1_router
  │   └── routes/
  │       └── __init__.py    # Re-exports from src.api.routes
  └── v2/ (futuro)
      ├── __init__.py        # v2_router
      └── routes/
          ├── keys.py        # Overrides específicos da v2
          └── ...
```

## 🔄 Como Criar uma Nova Versão (v2)

### **1. Criar estrutura v2**
```bash
mkdir -p src/api/v2/routes
touch src/api/v2/__init__.py
touch src/api/v2/routes/__init__.py
```

### **2. Criar `src/api/v2/__init__.py`**
```python
"""
API v2 Package
"""

from fastapi import APIRouter
from .routes import (
    health_router,
    home_router,
    projects_router,
    keys_router,  # v2 version
    scopes_router,
    # ... outros routers
)

# Create v2 API router
v2_router = APIRouter(prefix="/v2")

# Include all v2 routes
v2_router.include_router(health_router)
v2_router.include_router(home_router)
v2_router.include_router(projects_router)
v2_router.include_router(keys_router)
v2_router.include_router(scopes_router)
# ... incluir outros routers

__all__ = ["v2_router"]
```

### **3. Criar `src/api/v2/routes/__init__.py`**
```python
"""
API v2 Routes
Import specific v2 implementations or fallback to v1.
"""

# Rotas que mudaram na v2
from .keys import router as keys_router  # Nova implementação v2

# Rotas que não mudaram (usar v1)
from src.api.v1.routes import (
    health_router,
    home_router,
    projects_router,
    scopes_router,
    # ... outras rotas sem mudanças
)

__all__ = [
    "health_router",
    "home_router", 
    "projects_router",
    "keys_router",  # v2 version
    "scopes_router",
]
```

### **4. Criar endpoint v2 modificado**

**Exemplo: `src/api/v2/routes/keys.py`**
```python
"""
API v2 routes for API Key management.
Breaking changes from v1:
- Response format changed
- New required fields
- Removed deprecated fields
"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.connection import get_session
from src.database.repositories.api_key_repository import api_key_repository
from src.database.models import AKMAPIKey
from src.api.auth_middleware import PermissionChecker
# Import v2-specific models
from .models import APIKeyCreateV2, APIKeyResponseV2

router = APIRouter(prefix="/keys", tags=["API Keys"])


@router.post("", response_model=APIKeyResponseV2, status_code=status.HTTP_201_CREATED)
async def create_api_key(
    key_data: APIKeyCreateV2,  # v2 model
    api_key: AKMAPIKey = Depends(PermissionChecker(["akm:keys:write"])),
    session: AsyncSession = Depends(get_session)
):
    """
    Create a new API key (v2).
    
    **Breaking changes from v1:**
    - Response now includes `created_by` field
    - `project_id` is now required
    - Removed `owner` field (replaced by `created_by`)
    """
    # v2 logic here
    pass
```

### **5. Atualizar `src/api/versioning.py`**
```python
class APIVersion(str, Enum):
    """Supported API versions."""
    V1 = "v1"
    V2 = "v2"  # ✅ Adicionar

# Update latest version
LATEST_VERSION = APIVersion.V2

# Mark v1 as deprecated (opcional)
DEPRECATED_VERSIONS: set[APIVersion] = {APIVersion.V1}
```

### **6. Registrar v2 no `main.py`**
```python
from src.api.v1 import v1_router
from src.api.v2 import v2_router  # ✅ Importar

# Include versioned API routes
app.include_router(v1_router, prefix="/akm")
app.include_router(v2_router, prefix="/akm")  # ✅ Adicionar
```

## 🎛️ Headers de Versionamento

Clientes podem especificar a versão via header:

```bash
# Usando URL (recomendado)
curl https://api.example.com/akm/v1/keys

# Usando header (alternativa)
curl -H "X-API-Version: v1" https://api.example.com/akm/keys
```

## 📦 Modelos por Versão

### **Opção 1: Modelos compartilhados**
```
src/api/models/
  ├── __init__.py
  ├── api_keys.py      # Usado por todas as versões
  └── projects.py
```

### **Opção 2: Modelos versionados**
```
src/api/
  ├── v1/
  │   └── models/
  │       ├── __init__.py
  │       └── api_keys.py  # Modelos v1
  └── v2/
      └── models/
          ├── __init__.py
          └── api_keys.py  # Modelos v2 (com mudanças)
```

**Recomendação**: Use modelos compartilhados quando possível e crie versões específicas apenas quando houver breaking changes.

## 🚦 Ciclo de Vida de Versões

### **1. Active (Ativa)**
- Versão totalmente suportada
- Recebe novas features
- Recebe bugfixes

### **2. Deprecated (Depreciada)**
```python
DEPRECATED_VERSIONS: set[APIVersion] = {APIVersion.V1}
```
- Ainda funciona mas mostra warnings
- Recebe apenas bugfixes críticos
- Clientes devem migrar

**Response headers:**
```
X-API-Deprecated: true
X-API-Deprecated-Message: API version v1 is deprecated. Please migrate to v2.
```

### **3. Sunset (Desativada)**
```python
SUNSET_VERSIONS: set[APIVersion] = {APIVersion.V1}
```
- Não funciona mais
- Retorna HTTP 410 Gone
- Força migração

**Response:**
```json
{
  "status": "error",
  "error_message": "API version v1 has been sunset and is no longer available.",
  "current_version": "v2"
}
```

## 🧪 Testando Versões

### **Testes Unitários**
```python
# tests/unit/v1/test_keys.py
async def test_create_key_v1():
    # Testa comportamento v1
    pass

# tests/unit/v2/test_keys.py
async def test_create_key_v2():
    # Testa comportamento v2
    pass
```

### **Testes de Integração**
```python
# tests/integration/test_versioning.py
async def test_v1_endpoint():
    response = await client.get("/akm/v1/keys")
    assert response.status_code == 200

async def test_v2_endpoint():
    response = await client.get("/akm/v2/keys")
    assert response.status_code == 200

async def test_deprecated_warning():
    response = await client.get("/akm/keys")  # legacy
    assert "X-API-Deprecated" in response.headers
```

## 📝 Documentação

Cada versão tem sua própria documentação Swagger:

- **v1**: `https://api.example.com/docs?version=v1`
- **v2**: `https://api.example.com/docs?version=v2`

### **Configurar no OpenAPI**
```python
app = FastAPI(
    title="API Key Management Service",
    version="2.0.0",  # Versão do app
    openapi_tags=[
        {
            "name": "API Keys (v1)",
            "description": "v1 endpoints (deprecated)"
        },
        {
            "name": "API Keys (v2)",
            "description": "v2 endpoints (current)"
        }
    ]
)
```

## 🎯 Boas Práticas

### ✅ **DO**
1. **Versione breaking changes**: Mudanças que quebram contratos existentes
2. **Documente diferenças**: Deixe claro o que mudou entre versões
3. **Mantenha compatibilidade**: v1 deve continuar funcionando após v2
4. **Deprecie gradualmente**: Avise com antecedência (3-6 meses)
5. **Use semantic versioning**: v1, v2, v3 (não v1.1, v1.2)

### ❌ **DON'T**
1. **Não quebre v1 ao lançar v2**: Versões devem coexistir
2. **Não remova versões sem aviso**: Período de depreciação é obrigatório
3. **Não misture lógica**: Cada versão deve ter código separado
4. **Não versione bugfixes**: Correções vão para todas as versões ativas

## 🔄 Migration Guide para Clientes

### **De Legacy (sem versão) → v1**
```bash
# Antes
curl https://api.example.com/akm/keys

# Depois
curl https://api.example.com/akm/v1/keys
```

### **De v1 → v2**
Ver documento específico: `docs/MIGRATION_V1_TO_V2.md`

## 📊 Monitoramento

### **Métricas importantes**
- Uso por versão (% requests v1 vs v2)
- Taxa de erro por versão
- Latência por versão
- Clientes ainda usando versões deprecated

### **Logs**
```python
logger.info(
    "API request",
    version="v1",
    endpoint="/keys",
    deprecated=True
)
```

## 🚀 Roadmap

| Versão | Status | Lançamento | Sunset |
|--------|--------|-----------|--------|
| v1 | Active | 2024-01 | TBD |
| v2 | Planned | 2025-Q2 | - |

---

## 📚 Recursos

- [API Versioning Best Practices](https://www.baeldung.com/rest-versioning)
- [FastAPI Router Documentation](https://fastapi.tiangolo.com/tutorial/bigger-applications/)
- [Stripe API Versioning](https://stripe.com/docs/api/versioning) (referência de mercado)
