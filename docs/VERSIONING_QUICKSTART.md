# Quick Start: API Versioning

## ✅ O que foi implementado

Seu projeto agora suporta **versionamento de API por URL**:

### **URLs Novas (Recomendadas)**
```
GET  /akm/v1/keys
POST /akm/v1/keys
GET  /akm/v1/projects
GET  /akm/v1/scopes
... todas as rotas
```

### **URLs Legacy (Deprecated)**
```
GET  /akm/keys       → ⚠️ Deprecated
POST /akm/keys       → ⚠️ Deprecated
GET  /akm/projects   → ⚠️ Deprecated
```

## 🚀 Testando Agora

### **1. Inicie o servidor**
```bash
uvicorn main:app --reload
```

### **2. Teste endpoint versionado**
```bash
# Endpoint v1 (recomendado)
curl http://localhost:8000/akm/v1/keys

# Verifique os headers na resposta:
# X-API-Version: v1
# X-API-Latest-Version: v1
```

### **3. Teste endpoint legacy**
```bash
# Endpoint sem versão (deprecated)
curl -i http://localhost:8000/akm/keys

# Verifique os headers de depreciação:
# X-API-Deprecated: true
# X-API-Deprecated-Message: Use /akm/v1 instead
# X-API-Sunset-Date: 2026-01-01
```

## 📁 Arquivos Criados

### **1. Estrutura de Versionamento**
```
src/api/
  ├── versioning.py                    # Utilitários de versão
  ├── v1/
  │   ├── __init__.py                  # Router v1
  │   └── routes/__init__.py           # Re-exports das rotas
  └── middleware/
      └── versioning.py                # Middleware de warnings
```

### **2. Documentação**
```
docs/
  ├── API_VERSIONING.md               # Guia completo (como criar v2)
  └── MIGRATION_VERSIONING.md         # Guia de migração para clientes
```

### **3. Testes**
```
tests/integration/
  └── test_versioning.py               # 14 testes ✅ (100% passing)
```

## 🎯 Próximos Passos

### **Curto Prazo (agora)**
1. ✅ Estrutura criada
2. ✅ Middleware configurado
3. ✅ Testes passando
4. 🔄 **Comunique aos clientes**: Atualize para usar `/akm/v1/`

### **Médio Prazo (quando precisar de breaking changes)**
1. Crie `src/api/v2/` seguindo o guia em `docs/API_VERSIONING.md`
2. Implemente mudanças na v2
3. Marque v1 como deprecated
4. Atualize `LATEST_VERSION` em `versioning.py`

### **Longo Prazo (após 12+ meses)**
1. Remova rotas legacy (`/akm/keys`)
2. Sunset v1 se necessário (após v2 estar estável)

## 📊 Monitoramento

Os logs já registram automaticamente:

```json
{
  "level": "warning",
  "message": "Legacy (unversioned) endpoint accessed: /akm/keys",
  "recommended_path": "/akm/v1/keys"
}
```

## 🔑 Headers de Resposta

Toda resposta da API agora inclui:

```
X-API-Version: v1                    # Versão usada
X-API-Latest-Version: v1             # Última versão disponível
X-Correlation-ID: ...                # ID de correlação

# Se legacy:
X-API-Deprecated: true
X-API-Deprecated-Message: Use /akm/v1 instead
X-API-Sunset-Date: 2026-01-01
```

## 💡 Dicas

### **Para Desenvolvedores**
- Use sempre `/akm/v1/` em novos códigos
- Consulte `docs/API_VERSIONING.md` para criar v2
- Testes em `tests/integration/test_versioning.py`

### **Para Clientes da API**
- Migre de `/akm/keys` → `/akm/v1/keys`
- Monitore header `X-API-Deprecated`
- Consulte `docs/MIGRATION_VERSIONING.md`

## 📚 Documentação Completa

- **`docs/API_VERSIONING.md`** - Como criar versões, gerenciar ciclo de vida
- **`docs/MIGRATION_VERSIONING.md`** - Guia de migração para clientes
- **`src/api/versioning.py`** - Código de versionamento
- **`src/middleware/versioning.py`** - Middleware de deprecation warnings

## ✅ Checklist de Validação

- [x] Endpoints versionados funcionando (`/akm/v1/*`)
- [x] Endpoints legacy funcionando com warnings
- [x] Headers de versão nas respostas
- [x] Headers de depreciação em legacy routes
- [x] Middleware de versionamento ativo
- [x] Logs de uso de endpoints deprecated
- [x] 14 testes de versionamento passando
- [x] Documentação completa criada
- [x] Estrutura preparada para v2

## 🎓 Exemplo de Código Cliente

### **Python**
```python
import requests

# ✅ Recomendado (versionado)
response = requests.get("https://api.example.com/akm/v1/keys")

# ⚠️ Deprecated (legacy)
response = requests.get("https://api.example.com/akm/keys")
if response.headers.get("X-API-Deprecated") == "true":
    print(f"Warning: {response.headers['X-API-Deprecated-Message']}")
```

### **JavaScript**
```javascript
// ✅ Recomendado (versionado)
const response = await fetch('https://api.example.com/akm/v1/keys');

// ⚠️ Deprecated (legacy)
const response = await fetch('https://api.example.com/akm/keys');
if (response.headers.get('x-api-deprecated') === 'true') {
  console.warn(response.headers.get('x-api-deprecated-message'));
}
```

---

**🚀 Seu projeto está pronto para versionamento de API!**

Comece usando `/akm/v1/` em todos os novos desenvolvimentos.
