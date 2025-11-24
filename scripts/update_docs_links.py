"""Update docs_index.html links from markdown to HTML"""
import re
from pathlib import Path

# Read the file
index_path = Path("src/api/static/docs_index.html")
content = index_path.read_text(encoding='utf-8')

# Mapping of markdown file names to HTML paths
replacements = {
    'DEVELOPER_GUIDE.md': 'guides/developer_guide.html',
    'AUTHENTICATION.md': 'guides/authentication.html',
    'ADMINISTRATION.md': 'guides/public/guides/admnistration.html.html',
    'QUICKSTART.md': 'guides/quickstart.html',
    'SCOPES_BULK_INSERT.md': 'guides/scopes_bulk_insert.html',
    'OPENAPI_SCOPE_GENERATION.md': 'guides/openapi_scope_generation.html',
    'BULK_SCOPES.md': 'admin/bulk_scopes.html',
    'BULK_SCOPES_EXAMPLES.md': 'guides/bulk_scopes_examples.html',
    'WEBHOOKS.md': 'guides/webhooks.html',
    'ALERTS.md': 'guides/alerts.html',
    'CONFIGURATION_GUIDE.md': 'guides/configuration_guide.html',
    'ENVIRONMENT.md': 'operation/environment.html',
    'SENSITIVE_FIELDS.md': 'admin/sensitive_fields.html',
    'SENSITIVE_FIELDS_USAGE.md': 'guides/sensitive_fields_usage.html',
    'AUDIT_SYSTEM.md': 'admin/audit_system.html',
    'AUDIT_QUICK_START.md': 'admin/audit_quick_start.html',
    'AKM_SYSTEM.md': 'admin/akm_system.html',
    'API_KEY_MANAGEMENT.md': 'admin/api_key_management.html',
    'API_VERSIONING.md': 'admin/api_versioning.html',
    'DEPLOYMENT.md': 'admin/deployment.html',
    'LOGGING.md': 'operation/logging.html',
    'LOGGING_INSTRUMENTATION.md': 'operation/logging_instrumentation.html',
    'TESTING.md': 'admin/testing.html',
    'GITHUB_SECRETS_SETUP.md': 'operation/github_secrets_setup.html',
    'GIT_ACTIONS_SECRETS_BESTPRACTICES.md': 'operation/git_actions_secrets.html',
    'AUTHENTICATION_SUMMARY.md': 'admin/authentication_summary.html',
    'SENSITIVE_FIELDS_IMPLEMENTATION_SUMMARY.md': 'admin/sensitive_fields_implementation.html',
    'OPENAPI_EXAMPLES.md': 'guides/openapi_examples.html',
    'DYNAMIC_CONFIGURATION.md': 'admin/dynamic_configuration.html',
    'AUDIT_IMPLEMENTATION_SUMMARY.md': 'admin/audit_implementation_summary.html',
    'MIGRATION.md': 'admin/migration.html',
    'REFACTORING_SUMMARY.md': 'admin/refactoring_summary.html',
    'ARCHITECTURE_ISSUES_AND_IMPROVEMENTS.md': 'admin/architecture_issues.html',
}

# Replace all markdown links with HTML links
for md_file, html_path in replacements.items():
    # Pattern: href="docs/FILENAME.md"
    pattern = f'href="docs/{md_file}"'
    replacement = f'href="/{html_path}"'
    content = content.replace(pattern, replacement)

# Write back
index_path.write_text(content, encoding='utf-8')
print("✅ Updated docs_index.html links to HTML versions")
