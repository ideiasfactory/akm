#!/usr/bin/env python3
"""Drop all tables and reset database"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database.connection import get_session
from sqlalchemy import text


async def main():
    async for session in get_session():
        print('\n' + '=' * 80)
        print('Dropping All Database Tables')
        print('=' * 80 + '\n')
        
        try:
            # Drop alembic version table
            print('Dropping alembic_version table...')
            await session.execute(text('DROP TABLE IF EXISTS alembic_version CASCADE'))
            await session.commit()
            print('✅ alembic_version dropped')
            
            # Get all tables
            print('\nFetching table list...')
            result = await session.execute(text("""
                SELECT tablename FROM pg_tables 
                WHERE schemaname = 'public' 
                AND tablename NOT LIKE 'pg_%'
                AND tablename NOT LIKE 'sql_%'
            """))
            
            tables = [row[0] for row in result.fetchall()]
            
            if tables:
                print(f'\nFound {len(tables)} tables to drop:')
                for table in tables:
                    print(f'  - {table}')
                
                print('\nDropping tables...')
                for table in tables:
                    await session.execute(text(f'DROP TABLE IF EXISTS "{table}" CASCADE'))
                    print(f'  ✅ Dropped: {table}')
                
                await session.commit()
                print(f'\n✅ All {len(tables)} tables dropped successfully')
            else:
                print('\n⚠️  No tables found (database is already clean)')
            
        except Exception as e:
            print(f'\n❌ Error: {e}')
            import traceback
            traceback.print_exc()
            return 1
        
        print('\n' + '=' * 80)
        print('✅ Database Reset Complete')
        print('=' * 80 + '\n')
        
        break
    
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
