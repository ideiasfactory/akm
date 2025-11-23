# Migration Guide: Versionamento de API

## 🎯 Mudanças Implementadas

### ✅ **O que foi feito:**

1. **Estrutura de versionamento criada**
   - `src/api/v1/` - API v1 (atual)
   - `src/api/versioning.py` - Utilitários de versionamento
   - `src/middleware/versioning.py` - Middleware de depreciação

2. **URLs versionadas disponíveis**
   ```
   /akm/v1/keys        ✅ Nova (recomendada)
   /akm/v1/projects    ✅ Nova (recomendada)
   /akm/v1/scopes      ✅ Nova (recomendada)
   ... todas as rotas
   ```

3. **URLs legacy mantidas (deprecated)**
   ```
   /akm/keys          ⚠️ Legacy (funciona mas deprecated)
   /akm/projects      ⚠️ Legacy (funciona mas deprecated)
   /akm/scopes        ⚠️ Legacy (funciona mas deprecated)
   ```

4. **Headers de resposta adicionados**
   ```
   X-API-Version: v1
   X-API-Latest-Version: v1
   X-API-Deprecated: true (somente em rotas legacy)
   X-API-Deprecated-Message: Mensagem de aviso
   X-API-Sunset-Date: 2026-01-01
   ```

## 🔄 Migração para Clientes

### **Antes (Legacy)**
```bash
curl -H "X-API-Key: akm_xxx" \
  https://api.example.com/akm/keys
```

### **Depois (Versionado)**
```bash
curl -H "X-API-Key: akm_xxx" \
  https://api.example.com/akm/v1/keys
```

**⚠️ Importante**: As rotas legacy ainda funcionam mas serão removidas no futuro!

## 📝 Exemplo de Resposta

### **Rota Versionada (Recomendado)**
```bash
$ curl -i https://api.example.com/akm/v1/keys

HTTP/1.1 200 OK
X-API-Version: v1
X-API-Latest-Version: v1
X-Correlation-ID: 123e4567-e89b-12d3-a456-426614174000
...
```

### **Rota Legacy (Deprecated)**
```bash
$ curl -i https://api.example.com/akm/keys

HTTP/1.1 200 OK
X-API-Version: legacy
X-API-Latest-Version: v1
X-API-Deprecated: true
X-API-Deprecated-Message: Unversioned endpoints are deprecated. Use /akm/v1 instead.
X-API-Sunset-Date: 2026-01-01
X-Correlation-ID: 123e4567-e89b-12d3-a456-426614174000
...
```

## 🚀 Como Criar v2 no Futuro

Quando precisar fazer breaking changes:

### **1. Criar estrutura v2**
```bash
mkdir -p src/api/v2/routes
```

### **2. Criar arquivo v2 específico**

**src/api/v2/routes/keys.py** (exemplo)
```python
"""
API v2 routes for API Keys.

Breaking changes from v1:
- Changed response format
- Added required field: project_id
- Removed field: owner (use created_by instead)
"""

from fastapi import APIRouter, Depends
from src.api.models.api_keys import APIKeyCreateV2, APIKeyResponseV2

router = APIRouter(prefix="/keys", tags=["API Keys (v2)"])

@router.post("", response_model=APIKeyResponseV2)
async def create_api_key_v2(key_data: APIKeyCreateV2, ...):
    """
    Create API key (v2).
    
    **Changes from v1:**
    - project_id is now required
    - Response includes created_by field
    """
    # v2 implementation
    pass
```

### **3. Criar router v2**

**src/api/v2/__init__.py**
```python
from fastapi import APIRouter
from .routes import keys_router  # v2 version
from src.api.v1.routes import (  # Reuse v1 for unchanged routes
    health_router,
    projects_router,
    scopes_router,
)

v2_router = APIRouter(prefix="/v2")
v2_router.include_router(keys_router)  # v2 version
v2_router.include_router(projects_router)  # v1 version (sem mudanças)
v2_router.include_router(scopes_router)  # v1 version (sem mudanças)
```

### **4. Registrar v2 no main.py**
```python
from src.api.v1 import v1_router
from src.api.v2 import v2_router  # Import

# Register routes
app.include_router(v1_router, prefix="/akm")
app.include_router(v2_router, prefix="/akm")  # Add
```

### **5. Atualizar versioning.py**
```python
class APIVersion(str, Enum):
    V1 = "v1"
    V2 = "v2"  # Add

LATEST_VERSION = APIVersion.V2  # Update
DEPRECATED_VERSIONS = {APIVersion.V1}  # Mark v1 as deprecated
```

### **6. URLs disponíveis**
```
/akm/v1/keys       → v1 (deprecated)
/akm/v2/keys       → v2 (current)
/akm/keys          → legacy (removed ou redirect to v2)
```

## 📊 Monitoramento

### **Logs de Uso**
O sistema já loga automaticamente:

```json
{
  "level": "warning",
  "message": "Legacy (unversioned) endpoint accessed: /akm/keys",
  "correlation_id": "...",
  "path": "/akm/keys",
  "recommended_path": "/akm/v1/keys"
}
```

```json
{
  "level": "warning",
  "message": "Deprecated API version accessed: v1",
  "version": "v1",
  "latest_version": "v2"
}
```

### **Métricas Sugeridas**
- Contagem de requests por versão (v1, v2, legacy)
- Taxa de uso de versões deprecated
- Clientes ainda usando legacy endpoints

## 🎯 Checklist de Migration

Para migrar seus clientes:

### **Fase 1: Comunicação (Agora)**
- [ ] Enviar email para clientes sobre versionamento
- [ ] Atualizar documentação da API
- [ ] Adicionar avisos no Swagger/Docs
- [ ] Publicar blog post sobre mudança

### **Fase 2: Transição (3-6 meses)**
- [ ] Clientes começam a usar `/akm/v1/`
- [ ] Monitorar uso de endpoints legacy
- [ ] Oferecer suporte para migração
- [ ] Mostrar warnings em responses legacy

### **Fase 3: Depreciação (6-12 meses)**
- [ ] Marcar rotas legacy como deprecated
- [ ] Adicionar headers de sunset
- [ ] Enviar avisos finais
- [ ] Atualizar código de exemplo

### **Fase 4: Remoção (12+ meses)**
- [ ] Remover rotas legacy do código
- [ ] Atualizar testes
- [ ] Atualizar documentação
- [ ] Celebrar! 🎉

## 🧪 Testando Versionamento

### **Testar rota versionada**
```bash
curl -H "X-API-Key: akm_xxx" \
  http://localhost:8000/akm/v1/keys
```

### **Testar rota legacy (deve mostrar warnings)**
```bash
curl -i -H "X-API-Key: akm_xxx" \
  http://localhost:8000/akm/keys

# Verificar headers:
# X-API-Deprecated: true
# X-API-Deprecated-Message: ...
```

### **Testar header de versionamento**
```bash
curl -H "X-API-Key: akm_xxx" \
  -H "X-API-Version: v1" \
  http://localhost:8000/akm/keys
```

## 📚 Recursos Criados

1. **`docs/API_VERSIONING.md`** - Guia completo de versionamento
2. **`src/api/versioning.py`** - Utilitários de versão
3. **`src/api/v1/`** - Estrutura v1
4. **`src/middleware/versioning.py`** - Middleware de warnings
5. **Este guia** - Migration guide

## ❓ FAQ

**P: As rotas antigas `/akm/keys` vão parar de funcionar?**
R: Não imediatamente. Elas continuam funcionando mas mostram warnings. Serão removidas após período de depreciação (12+ meses).

**P: Preciso atualizar meu código agora?**
R: Recomendamos migrar para `/akm/v1/keys` o quanto antes para evitar problemas futuros.

**P: Como sei qual versão estou usando?**
R: Verifique o header `X-API-Version` na resposta ou use sempre o prefixo `/v1/` nas URLs.

**P: E se eu quiser usar sempre a última versão?**
R: Use o header `X-API-Version: latest` ou consulte `X-API-Latest-Version` na resposta.

**P: Posso usar v1 e v2 ao mesmo tempo?**
R: Sim! Versões coexistem. Você pode migrar gradualmente endpoint por endpoint.

---

**📧 Dúvidas?** Entre em contato com o time de desenvolvimento.
