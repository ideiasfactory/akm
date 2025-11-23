#!/usr/bin/env python3
"""
Script para gerar/atualizar a API Key de administrador do sistema.

Este script:
1. Gera uma nova chave admin com escopo akm:* (acesso total)
2. Revoga a chave anterior (se existir)
3. Salva a nova chave em ADMIN_API_KEY.txt

Uso:
    python generate_admin_key.py
"""

import asyncio
import sys
from datetime import datetime
from pathlib import Path

# Adiciona o diretório raiz ao path para importar módulos
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database.connection import get_async_session
from src.database.repositories.api_key_repository import APIKeyRepository
from src.database.repositories.project_repository import ProjectRepository
from src.database.repositories.scope_repository import ScopeRepository
from src.database.models import AKMAPIKey
from sqlalchemy import select


async def revoke_previous_admin_keys(session, project_id: int):
    """Revoga todas as chaves admin anteriores do projeto"""
    stmt = select(AKMAPIKey).where(
        AKMAPIKey.project_id == project_id,
        AKMAPIKey.is_active == True
    )
    result = await session.execute(stmt)
    old_keys = result.scalars().all()
    
    revoked_count = 0
    for old_key in old_keys:
        old_key.is_active = False
        old_key.revoked_at = datetime.utcnow()
        revoked_count += 1
    
    if revoked_count > 0:
        await session.commit()
        print(f"✓ {revoked_count} chave(s) anterior(es) revogada(s)")
    
    return revoked_count


async def generate_admin_key():
    """Gera uma nova chave de administrador"""
    
    api_key_repo = APIKeyRepository()
    project_repo = ProjectRepository()
    scope_repo = ScopeRepository()
    
    print("\n" + "="*80)
    print("GERAÇÃO DE CHAVE DE ADMINISTRADOR - API KEY MANAGEMENT")
    print("="*80 + "\n")
    
    async with get_async_session() as session:
        # 1. Busca o projeto "admin" (ID 1)
        project = await project_repo.get_by_id(session, 1)
        
        if not project:
            print("❌ ERRO: Projeto admin não encontrado!")
            print("Execute primeiro: python scripts/reset_database.py")
            return
        
        print(f"✓ Projeto: {project.name} (ID: {project.id}, Prefix: {project.prefix})")
        
        # 2. Revoga chaves anteriores
        revoked = await revoke_previous_admin_keys(session, project.id)
        
        # 3. Busca o escopo akm:* (escopo master)
        master_scope = await scope_repo.get_by_name(session, "akm:*")
        
        if not master_scope:
            print("❌ ERRO: Escopo master 'akm:*' não encontrado!")
            return
        
        print(f"✓ Escopo: {master_scope.scope_name} (ID: {master_scope.id})")
        
        # 4. Gera nova chave
        print("\n🔄 Gerando nova chave de administrador...")
        
        api_key_record, plain_key = await api_key_repo.create_key(
            session=session,
            project_id=project.id,
            name="Admin Master Key",
            scopes=["akm:*"],
            description="Master admin key with full system access",
            expires_at=None,  # Sem expiração
            auto_generate=True
        )
        
        await session.commit()
        await session.refresh(api_key_record)
        
        # 5. Busca estatísticas do sistema
        all_scopes = await scope_repo.list_all(session)
        
        # Conta sensitive fields globais
        from src.database.models import AKMSensitiveField
        from sqlalchemy import func
        global_fields_count = await session.scalar(
            select(func.count()).select_from(AKMSensitiveField).where(AKMSensitiveField.project_id.is_(None))
        )
        
        # Conta webhook events
        from src.database.models import AKMWebhookEvent
        webhook_events_count = await session.scalar(
            select(func.count()).select_from(AKMWebhookEvent)
        )
        
        print("✓ Chave gerada com sucesso!\n")
        
        # 6. Salva em arquivo
        output_file = Path(__file__).parent.parent / "ADMIN_API_KEY.txt"
        
        content = f"""Admin API Key (Generated: {datetime.utcnow().isoformat()})
================================================================================
{plain_key}
================================================================================

Project ID: {project.id}
Project Prefix: {project.prefix}
API Key ID: {api_key_record.id}
Scope ID: {master_scope.id} ({master_scope.scope_name})

Scopes: {master_scope.scope_name} (full system access)
Total Scopes: {len(all_scopes)}
Total Global Sensitive Fields: {global_fields_count or 0}
Total Webhook Events: {webhook_events_count or 0}

================================================================================
GLOBAL SENSITIVE FIELDS (apply to ALL projects):
================================================================================
"""
        
        # Lista sensitive fields globais
        global_fields_stmt = select(AKMSensitiveField).where(
            AKMSensitiveField.project_id.is_(None)
        ).order_by(AKMSensitiveField.field_name)
        global_fields_result = await session.execute(global_fields_stmt)
        global_fields = global_fields_result.scalars().all()
        
        for field in global_fields:
            content += f"  - {field.field_name}\n"
        
        content += """
Projects can override these or add their own project-specific fields.

================================================================================
IMPORTANT: Keep this key secure and never commit it to version control!
================================================================================
"""
        
        output_file.write_text(content, encoding="utf-8")
        
        print("="*80)
        print("NOVA CHAVE DE ADMINISTRADOR")
        print("="*80)
        print(f"\n{plain_key}\n")
        print("="*80)
        print(f"\n✓ Chave salva em: {output_file}")
        print(f"✓ Project ID: {project.id}")
        print(f"✓ API Key ID: {api_key_record.id}")
        print(f"✓ Escopo: {master_scope.scope_name} (acesso total)")
        print(f"✓ Status: {'Ativa' if api_key_record.is_active else 'Inativa'}")
        print(f"✓ Expira em: {'Nunca' if not api_key_record.expires_at else api_key_record.expires_at.isoformat()}")
        print("\n⚠️  IMPORTANTE: Guarde esta chave em local seguro!")
        print("⚠️  Não commite o arquivo ADMIN_API_KEY.txt no git!\n")
        

if __name__ == "__main__":
    try:
        asyncio.run(generate_admin_key())
    except KeyboardInterrupt:
        print("\n\n⚠️  Operação cancelada pelo usuário.")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ ERRO: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
