"""Script to check database structure."""
import os
from sqlalchemy import create_engine, inspect

# Use direct connection
db_url = "postgresql://neondb_owner:npg_W0KogSXdiG6Z@ep-falling-morning-ac6qv476-pooler.sa-east-1.aws.neon.tech/neondb?sslmode=require"
db_url = db_url.replace('postgresql://', 'postgresql+psycopg2://')

engine = create_engine(db_url)
inspector = inspect(engine)

tables_to_check = [
    'akm_scopes',
    'akm_api_keys', 
    'akm_webhooks',
    'akm_alert_rules',
    'akm_sensitive_fields'
]

print("\n" + "="*70)
print("ESTRUTURA DAS TABELAS NO BANCO DE DADOS")
print("="*70)

for table_name in tables_to_check:
    if table_name in inspector.get_table_names():
        print(f"\n📋 {table_name.upper()}")
        print("-" * 70)
        columns = inspector.get_columns(table_name)
        for col in columns:
            nullable = "NULL" if col['nullable'] else "NOT NULL"
            print(f"  {col['name']:30} {str(col['type']):20} {nullable}")
    else:
        print(f"\n❌ Tabela {table_name} não encontrada")

print("\n" + "="*70)
