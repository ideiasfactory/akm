# Análise Arquitetural: Problemas e Melhorias - Multi-Tenancy

**Data**: 20 de Novembro de 2025  
**Status**: 🔴 CRÍTICO - Problemas de Design Multi-Tenant

---

## ❌ Problemas Identificados

### 1. **Falta de Relacionamento Projeto ↔ Escopo**

#### Problema
Atualmente, a tabela `akm_scopes` é **global** e não tem relacionamento com projetos:

```sql
-- Estrutura Atual (INCORRETA para multi-tenancy)
CREATE TABLE akm_scopes (
    id INTEGER PRIMARY KEY,
    scope_name VARCHAR(100) UNIQUE NOT NULL,  -- ❌ Único GLOBALMENTE
    description TEXT,
    is_active BOOLEAN,
    created_at TIMESTAMP
);

-- NÃO EXISTE:
-- project_id INTEGER REFERENCES akm_projects(id)
```

#### Consequências
1. **Todos os projetos compartilham os mesmos escopos** ❌
   - Projeto A cria escopo `akm:users:read`
   - Projeto B também quer criar `akm:users:read`
   - **CONFLITO**: scope_name é UNIQUE globalmente!

2. **Sem isolamento de dados** ❌
   - Um projeto pode ver todos os escopos do sistema
   - Não há como ter escopos específicos por projeto

3. **Integridade referencial fraca** ❌
   - API keys podem receber escopos de qualquer projeto
   - Exemplo: API key do Projeto A pode receber escopo do Projeto B

#### Como está agora
```
┌─────────────┐
│   Project   │
│   AKM Admin │
│   ID: 1     │
└──────┬──────┘
       │
       │ ❌ SEM RELACIONAMENTO
       │
       ▼
┌──────────────────┐
│     Scopes       │
│  (GLOBAL)        │
│ akm:projects:*   │
│ akm:keys:*       │
│ akm:scopes:*     │
└──────────────────┘
```

---

### 2. **Prefixo Hardcoded sem Relacionamento**

#### Problema
Os escopos usam prefixo `akm:` mas isso é apenas uma **convenção de nomenclatura**, não uma constraint do banco:

```python
# Convenção usada (apenas no código, não no DB)
"akm:projects:read"
"akm:keys:write"
"akm:sensitive-fields:*"
```

#### Consequências
1. **Não há validação no banco** ❌
   - Nada impede criar escopo `xyz:anything:here`
   - Projeto não tem campo `prefix` ou `namespace`

2. **Colisões entre projetos** ❌
   - Dois projetos diferentes podem querer o mesmo prefixo `akm:`
   - Sistema assume que `akm:` pertence ao projeto "AKM Admin"

3. **Hardcoded no código** ❌
   ```python
   # Em múltiplos lugares:
   AUDIT_READ_SCOPE = "akm:audit:read"
   READ_SCOPE = "akm:sensitive-fields:read"
   ```

#### Estrutura Atual do Projeto (INCOMPLETA)
```python
class AKMProject(Base):
    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True)
    description = Column(Text)
    is_active = Column(Boolean)
    
    # ❌ FALTAM:
    # prefix = Column(String(20), unique=True, nullable=False)  # Ex: "akm", "app1", "svc2"
    # namespace = Column(String(50), unique=True)  # Ex: "akm-admin", "app1-prod"
```

---

## 🎯 Arquitetura Correta para Multi-Tenancy

### Opção 1: **Escopos por Projeto** (Recomendado)

#### Modelo de Dados
```sql
-- Adicionar prefix ao projeto
ALTER TABLE akm_projects
ADD COLUMN prefix VARCHAR(20) UNIQUE NOT NULL DEFAULT 'akm';

-- Relacionar escopos com projetos
ALTER TABLE akm_scopes
ADD COLUMN project_id INTEGER REFERENCES akm_projects(id) ON DELETE CASCADE;

-- Mudar constraint UNIQUE
ALTER TABLE akm_scopes
DROP CONSTRAINT akm_scopes_scope_name_key;

ALTER TABLE akm_scopes
ADD CONSTRAINT uq_project_scope UNIQUE (project_id, scope_name);

-- Index para performance
CREATE INDEX idx_scopes_project ON akm_scopes(project_id, is_active);
```

#### Estrutura Revisada
```python
class AKMProject(Base):
    __tablename__ = "akm_projects"
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True, nullable=False)
    prefix = Column(String(20), unique=True, nullable=False)  # 🆕 "akm", "proj1"
    description = Column(Text)
    is_active = Column(Boolean, default=True)
    
    # Relationships
    api_keys = relationship("AKMAPIKey", back_populates="project")
    scopes = relationship("AKMScope", back_populates="project")  # 🆕


class AKMScope(Base):
    __tablename__ = "akm_scopes"
    
    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey("akm_projects.id", ondelete="CASCADE"), nullable=False)  # 🆕
    scope_name = Column(String(100), nullable=False)  # agora NÃO é unique global
    description = Column(Text)
    is_active = Column(Boolean, default=True)
    
    # Relationships
    project = relationship("AKMProject", back_populates="scopes")  # 🆕
    
    # Constraints
    __table_args__ = (
        UniqueConstraint("project_id", "scope_name", name="uq_project_scope"),  # 🆕 Unique por projeto
        Index("idx_scopes_project", "project_id", "is_active"),
    )
```

#### Como Ficaria
```
┌─────────────────────┐
│   Project: AKM      │
│   ID: 1             │
│   Prefix: "akm"     │
└──────────┬──────────┘
           │
           │ 1:N (project_id FK)
           ▼
┌──────────────────────┐
│   Scopes (Project 1) │
│  ├─ akm:projects:*   │
│  ├─ akm:keys:*       │
│  └─ akm:scopes:*     │
└──────────────────────┘

┌─────────────────────┐
│   Project: App1     │
│   ID: 2             │
│   Prefix: "app1"    │
└──────────┬──────────┘
           │
           │ 1:N (project_id FK)
           ▼
┌──────────────────────┐
│   Scopes (Project 2) │
│  ├─ app1:users:read  │  ✅ MESMO PADRÃO, SEM CONFLITO
│  ├─ app1:users:write │
│  └─ app1:admin:*     │
└──────────────────────┘
```

---

### Opção 2: **Escopos Globais + Namespace** (Alternativa)

Manter escopos globais mas adicionar validação de namespace:

```python
class AKMProject(Base):
    prefix = Column(String(20), unique=True, nullable=False)  # "akm"
    
    @validates('prefix')
    def validate_prefix(self, key, value):
        if not re.match(r'^[a-z][a-z0-9-]{1,19}$', value):
            raise ValueError("Invalid prefix format")
        return value


class AKMScope(Base):
    scope_name = Column(String(100), unique=True)  # Ainda global
    
    @validates('scope_name')
    def validate_scope_format(self, key, value):
        # Validar formato: <prefix>:<resource>:<action>
        parts = value.split(':')
        if len(parts) != 3:
            raise ValueError("Scope must be in format: prefix:resource:action")
        
        prefix, resource, action = parts
        
        # Verificar se prefix existe em algum projeto
        # (fazer query na session)
        
        return value
```

**Problema**: Ainda permite colisões e não garante isolamento por projeto.

---

## 🔧 Validações Necessárias

### 1. Validação de API Key ↔ Escopo
```python
class APIKeyRepository:
    async def create_key(
        self,
        session: AsyncSession,
        project_id: int,
        scopes: List[str],
        ...
    ):
        # ✅ VALIDAR: Todos os escopos pertencem ao projeto
        for scope_name in scopes:
            scope = await session.execute(
                select(AKMScope).where(
                    AKMScope.project_id == project_id,  # 🆕
                    AKMScope.scope_name == scope_name
                )
            )
            if not scope.scalar_one_or_none():
                raise ValueError(
                    f"Scope '{scope_name}' does not belong to project {project_id}"
                )
```

### 2. Validação de Prefixo em Escopos
```python
class ScopeRepository:
    async def create(
        self,
        session: AsyncSession,
        project_id: int,
        scope_name: str,
        ...
    ):
        # ✅ VALIDAR: Escopo começa com prefix do projeto
        project = await session.get(AKMProject, project_id)
        
        if not scope_name.startswith(f"{project.prefix}:"):
            raise ValueError(
                f"Scope must start with project prefix '{project.prefix}:'"
            )
```

---

## 📊 Comparação de Abordagens

| Aspecto | Atual (ERRADO) | Opção 1: Scopes/Projeto | Opção 2: Global + Validação |
|---------|----------------|-------------------------|------------------------------|
| **Isolamento** | ❌ Nenhum | ✅ Total | ⚠️ Parcial |
| **Integridade** | ❌ Fraca | ✅ Forte (FK) | ⚠️ Via código |
| **Escalabilidade** | ❌ Colisões | ✅ Sem limites | ⚠️ Limitada |
| **Multi-tenant** | ❌ Não suporta | ✅ Nativo | ⚠️ Simulado |
| **Performance** | ✅ Simples | ✅ Com índices | ⚠️ Queries complexas |
| **Migração** | - | ⚠️ Requer migração | ⚠️ Requer migração |

---

## 🚀 Plano de Migração (Opção 1)

### Fase 1: Adicionar Campos
```python
# Migration 005: Add project scope relationship

def upgrade():
    # Adicionar prefix ao projeto
    op.add_column('akm_projects', 
        sa.Column('prefix', sa.String(20), nullable=True)
    )
    
    # Atualizar projeto existente
    op.execute("UPDATE akm_projects SET prefix = 'akm' WHERE id = 1")
    
    # Tornar NOT NULL
    op.alter_column('akm_projects', 'prefix', nullable=False)
    op.create_unique_constraint('uq_project_prefix', 'akm_projects', ['prefix'])
    
    # Adicionar project_id aos escopos
    op.add_column('akm_scopes',
        sa.Column('project_id', sa.Integer(), nullable=True)
    )
    
    # Migrar escopos existentes para projeto 1
    op.execute("UPDATE akm_scopes SET project_id = 1")
    
    # Tornar NOT NULL e adicionar FK
    op.alter_column('akm_scopes', 'project_id', nullable=False)
    op.create_foreign_key(
        'fk_scope_project', 'akm_scopes', 'akm_projects',
        ['project_id'], ['id'], ondelete='CASCADE'
    )
    
    # Remover UNIQUE global, adicionar UNIQUE composto
    op.drop_constraint('akm_scopes_scope_name_key', 'akm_scopes')
    op.create_unique_constraint(
        'uq_project_scope', 'akm_scopes', ['project_id', 'scope_name']
    )
    
    # Criar índice
    op.create_index('idx_scopes_project', 'akm_scopes', ['project_id', 'is_active'])
```

### Fase 2: Atualizar Código
```python
# Repositórios
# Adicionar project_id em todas as queries de scopes

# Auth Middleware
# Verificar se scopes pertencem ao projeto da API key

# Routes
# Filtrar escopos pelo projeto do usuário
```

### Fase 3: Validações
```python
# Adicionar validações de integridade
# Testes de isolamento multi-tenant
```

---

## 📋 Recomendação Final

**Implementar Opção 1** (Escopos por Projeto) porque:

1. ✅ **Integridade referencial** via Foreign Keys
2. ✅ **Isolamento real** entre projetos
3. ✅ **Escalável** para múltiplos tenants
4. ✅ **Seguro** por design (não depende de código)
5. ✅ **Padrão de mercado** em sistemas multi-tenant

### Próximos Passos
1. Criar migration 005 com relacionamento projeto-escopo
2. Adicionar campo `prefix` na tabela `akm_projects`
3. Atualizar repositórios com validações de projeto
4. Atualizar auth middleware para verificar projeto
5. Criar testes de isolamento multi-tenant

---

## 🔍 Código Atual vs. Desejado

### Atual (INCORRETO)
```python
# Criar escopo sem verificar projeto
scope = AKMScope(
    scope_name="akm:users:read",  # ❌ Pode colidir
    description="Read users"
)

# API key pode receber qualquer escopo
api_key = AKMAPIKey(
    project_id=1,
    scopes=["other-project:admin:*"]  # ❌ Sem validação!
)
```

### Desejado (CORRETO)
```python
# Criar escopo vinculado ao projeto
scope = AKMScope(
    project_id=1,  # ✅ Vinculado ao projeto
    scope_name="akm:users:read",  # ✅ Unique por projeto
    description="Read users"
)

# Validação automática via FK
api_key = AKMAPIKey(
    project_id=1,
    scopes=[
        # ✅ Apenas escopos do projeto 1
        select from akm_scopes where project_id = 1
    ]
)
```

---

## 📚 Referências

- **Multi-tenancy Patterns**: https://docs.microsoft.com/en-us/azure/architecture/patterns/multi-tenancy
- **SaaS Database Design**: Row-level vs Schema-level isolation
- **Scope-based Authorization**: OAuth 2.0 patterns

---

**Conclusão**: O sistema atual **não é verdadeiramente multi-tenant**. Os escopos são compartilhados globalmente sem isolamento por projeto. É necessário implementar a Opção 1 para ter um sistema robusto e escalável.
