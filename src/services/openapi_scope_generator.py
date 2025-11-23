"""
Service for generating scopes from OpenAPI/Swagger specifications.
"""

import re
import json
import yaml
from typing import Dict, List, Any, Optional
from pathlib import Path
import httpx

from src.api.models.openapi_scopes import (
    OpenAPISourceType,
    ScopeGenerationStrategy,
    ScopeNamingConfig,
    GeneratedScope,
    OpenAPIScopeGenerationResponse,
    OpenAPIAnalysisResponse
)


class OpenAPIScopeGenerator:
    """Generator for creating scopes from OpenAPI specifications"""
    
    async def load_spec(
        self,
        source_type: OpenAPISourceType,
        source: Optional[str] = None,
        spec_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Load OpenAPI spec from various sources"""
        
        if source_type == OpenAPISourceType.JSON:
            if not spec_data:
                raise ValueError("spec_data is required for JSON source type")
            return spec_data
        
        if source_type == OpenAPISourceType.URL:
            if not source:
                raise ValueError("source URL is required for URL source type")
            return await self._load_from_url(source)
        
        if source_type == OpenAPISourceType.FILE:
            if not source:
                raise ValueError("source path is required for FILE source type")
            return await self._load_from_file(source)
        
        raise ValueError(f"Unsupported source type: {source_type}")
    
    async def _load_from_url(self, url: str) -> Dict[str, Any]:
        """Load spec from URL"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url)
            response.raise_for_status()
            
            content_type = response.headers.get('content-type', '')
            
            if 'yaml' in content_type or url.endswith(('.yaml', '.yml')):
                return yaml.safe_load(response.text)
            else:
                return response.json()
    
    async def _load_from_file(self, file_path: str) -> Dict[str, Any]:
        """Load spec from file"""
        path = Path(file_path)
        
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        content = path.read_text(encoding='utf-8')
        
        if path.suffix in ['.yaml', '.yml']:
            return yaml.safe_load(content)
        elif path.suffix == '.json':
            return json.loads(content)
        else:
            # Try to parse as JSON first, then YAML
            try:
                return json.loads(content)
            except json.JSONDecodeError:
                return yaml.safe_load(content)
    
    def analyze_spec(self, spec: Dict[str, Any]) -> OpenAPIAnalysisResponse:
        """Analyze OpenAPI spec and return statistics"""
        info = spec.get('info', {})
        paths = spec.get('paths', {})
        
        # Collect all operations
        operations = []
        http_methods = set()
        tags = set()
        
        for path, path_item in paths.items():
            for method, operation in path_item.items():
                if method.upper() in ['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'HEAD', 'OPTIONS']:
                    operations.append({
                        'path': path,
                        'method': method.upper(),
                        'operation': operation,
                        'tags': operation.get('tags', [])
                    })
                    http_methods.add(method.upper())
                    tags.update(operation.get('tags', []))
        
        # Estimate scopes for each strategy
        estimated_scopes = {}
        sample_scopes = {}
        
        # PATH_METHOD strategy
        estimated_scopes['path_method'] = len(operations)
        sample_scopes['path_method'] = [
            self._generate_scope_name_path_method(
                op['path'], op['method'], ScopeNamingConfig()
            )
            for op in operations[:5]
        ]
        
        # PATH_RESOURCE strategy
        resources = self._extract_resources_from_paths(list(paths.keys()))
        estimated_scopes['path_resource'] = len(resources) * len(http_methods)
        sample_scopes['path_resource'] = [
            f"api:{resource}:read"
            for resource in list(resources)[:5]
        ]
        
        # TAG_BASED strategy
        estimated_scopes['tag_based'] = len(tags) * len(http_methods)
        sample_scopes['tag_based'] = [
            f"api:{tag.lower().replace(' ', '_')}:read"
            for tag in list(tags)[:5]
        ]
        
        # OPERATION_ID strategy
        ops_with_id = [op for op in operations if op['operation'].get('operationId')]
        estimated_scopes['operation_id'] = len(ops_with_id)
        sample_scopes['operation_id'] = [
            f"api:{op['operation']['operationId']}:execute"
            for op in ops_with_id[:5]
        ]
        
        return OpenAPIAnalysisResponse(
            api_title=info.get('title', 'Unknown API'),
            api_version=info.get('version', '1.0.0'),
            total_paths=len(paths),
            total_operations=len(operations),
            http_methods=sorted(list(http_methods)),
            tags=sorted(list(tags)),
            estimated_scopes_by_strategy=estimated_scopes,
            sample_scopes=sample_scopes
        )
    
    def generate_scopes(
        self,
        spec: Dict[str, Any],
        strategy: ScopeGenerationStrategy,
        naming_config: ScopeNamingConfig,
        category: str,
        generate_wildcards: bool
    ) -> OpenAPIScopeGenerationResponse:
        """Generate scopes from OpenAPI spec"""
        
        info = spec.get('info', {})
        paths = spec.get('paths', {})
        
        warnings = []
        generated_scopes: List[GeneratedScope] = []
        
        # Collect operations
        operations = []
        for path, path_item in paths.items():
            for method, operation in path_item.items():
                if method.upper() in ['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'HEAD', 'OPTIONS']:
                    operations.append({
                        'path': path,
                        'method': method.upper(),
                        'operation': operation,
                        'tags': operation.get('tags', [])
                    })
        
        # Generate scopes based on strategy
        if strategy == ScopeGenerationStrategy.PATH_METHOD:
            generated_scopes = self._generate_path_method_scopes(
                operations, naming_config, category
            )
        
        elif strategy == ScopeGenerationStrategy.PATH_RESOURCE:
            generated_scopes = self._generate_path_resource_scopes(
                operations, naming_config, category, generate_wildcards
            )
        
        elif strategy == ScopeGenerationStrategy.TAG_BASED:
            generated_scopes = self._generate_tag_based_scopes(
                operations, naming_config, category, generate_wildcards
            )
        
        elif strategy == ScopeGenerationStrategy.OPERATION_ID:
            generated_scopes = self._generate_operation_id_scopes(
                operations, naming_config, category
            )
            
            # Check for missing operationIds
            missing_ids = [op for op in operations if not op['operation'].get('operationId')]
            if missing_ids:
                warnings.append(
                    f"{len(missing_ids)} operations missing operationId - these will be skipped"
                )
        
        # Deduplicate by scope_name
        unique_scopes = {}
        for scope in generated_scopes:
            if scope.scope_name not in unique_scopes:
                unique_scopes[scope.scope_name] = scope
        
        return OpenAPIScopeGenerationResponse(
            api_title=info.get('title', 'Unknown API'),
            api_version=info.get('version', '1.0.0'),
            total_scopes=len(unique_scopes),
            strategy_used=strategy,
            scopes=list(unique_scopes.values()),
            warnings=warnings
        )
    
    def _generate_path_method_scopes(
        self,
        operations: List[Dict],
        naming_config: ScopeNamingConfig,
        category: str
    ) -> List[GeneratedScope]:
        """Generate one scope per path + method combination"""
        scopes = []
        
        for op in operations:
            scope_name = self._generate_scope_name_path_method(
                op['path'], op['method'], naming_config
            )
            
            description = op['operation'].get('summary') or op['operation'].get('description') or \
                         f"{op['method']} {op['path']}"
            
            scopes.append(GeneratedScope(
                scope_name=scope_name,
                description=description[:500],  # Limit to 500 chars
                category=category,
                is_active=True,
                metadata={
                    'path': op['path'],
                    'method': op['method'],
                    'tags': op['tags']
                }
            ))
        
        return scopes
    
    def _generate_path_resource_scopes(
        self,
        operations: List[Dict],
        naming_config: ScopeNamingConfig,
        category: str,
        generate_wildcards: bool
    ) -> List[GeneratedScope]:
        """Generate CRUD scopes per resource"""
        scopes = []
        resources = {}
        
        # Group operations by resource
        for op in operations:
            resource = self._extract_resource_from_path(op['path'])
            action = naming_config.action_mapping.get(op['method'], 'execute')
            
            if resource not in resources:
                resources[resource] = {}
            
            if action not in resources[resource]:
                resources[resource][action] = []
            
            resources[resource][action].append(op)
        
        # Generate scopes
        for resource, actions in resources.items():
            for action, ops in actions.items():
                scope_name = f"{naming_config.namespace}:{resource}:{action}"
                
                # Build description from operations
                methods = sorted(set(op['method'] for op in ops))
                paths = sorted(set(op['path'] for op in ops))
                
                description = f"{action.capitalize()} operations for {resource} ({', '.join(methods)})"
                if len(paths) == 1:
                    description += f" - {paths[0]}"
                
                scopes.append(GeneratedScope(
                    scope_name=scope_name,
                    description=description[:500],
                    category=category,
                    is_active=True,
                    metadata={
                        'resource': resource,
                        'action': action,
                        'methods': methods,
                        'paths': paths
                    }
                ))
            
            # Generate wildcard scope
            if generate_wildcards:
                scopes.append(GeneratedScope(
                    scope_name=f"{naming_config.namespace}:{resource}:*",
                    description=f"Full access to {resource} resource",
                    category=category,
                    is_active=True,
                    metadata={
                        'resource': resource,
                        'wildcard': True
                    }
                ))
        
        return scopes
    
    def _generate_tag_based_scopes(
        self,
        operations: List[Dict],
        naming_config: ScopeNamingConfig,
        category: str,
        generate_wildcards: bool
    ) -> List[GeneratedScope]:
        """Generate scopes based on OpenAPI tags"""
        scopes = []
        tag_operations = {}
        
        # Group by tag and action
        for op in operations:
            tags = op['tags'] if op['tags'] else ['untagged']
            action = naming_config.action_mapping.get(op['method'], 'execute')
            
            for tag in tags:
                tag_clean = self._sanitize_name(tag)
                key = (tag_clean, action)
                
                if key not in tag_operations:
                    tag_operations[key] = []
                
                tag_operations[key].append(op)
        
        # Generate scopes
        tags_with_wildcards = set()
        
        for (tag, action), ops in tag_operations.items():
            scope_name = f"{naming_config.namespace}:{tag}:{action}"
            
            methods = sorted(set(op['method'] for op in ops))
            description = f"{action.capitalize()} operations for {tag} ({', '.join(methods)})"
            
            scopes.append(GeneratedScope(
                scope_name=scope_name,
                description=description[:500],
                category=category,
                is_active=True,
                metadata={
                    'tag': tag,
                    'action': action,
                    'methods': methods
                }
            ))
            
            tags_with_wildcards.add(tag)
        
        # Generate wildcard scopes
        if generate_wildcards:
            for tag in tags_with_wildcards:
                scopes.append(GeneratedScope(
                    scope_name=f"{naming_config.namespace}:{tag}:*",
                    description=f"Full access to {tag} operations",
                    category=category,
                    is_active=True,
                    metadata={
                        'tag': tag,
                        'wildcard': True
                    }
                ))
        
        return scopes
    
    def _generate_operation_id_scopes(
        self,
        operations: List[Dict],
        naming_config: ScopeNamingConfig,
        category: str
    ) -> List[GeneratedScope]:
        """Generate one scope per operationId"""
        scopes = []
        
        for op in operations:
            operation_id = op['operation'].get('operationId')
            
            if not operation_id:
                continue
            
            scope_name = f"{naming_config.namespace}:{operation_id}:execute"
            
            description = op['operation'].get('summary') or op['operation'].get('description') or \
                         f"Execute {operation_id}"
            
            scopes.append(GeneratedScope(
                scope_name=scope_name,
                description=description[:500],
                category=category,
                is_active=True,
                metadata={
                    'operation_id': operation_id,
                    'path': op['path'],
                    'method': op['method']
                }
            ))
        
        return scopes
    
    def _generate_scope_name_path_method(
        self,
        path: str,
        method: str,
        naming_config: ScopeNamingConfig
    ) -> str:
        """Generate scope name from path and method"""
        # Extract resource from path
        resource = self._extract_resource_from_path(path)
        
        # Get action from method
        action = naming_config.action_mapping.get(method, 'execute')
        
        # Build scope name
        return f"{naming_config.namespace}:{resource}_{method.lower()}:{action}"
    
    def _extract_resource_from_path(self, path: str) -> str:
        """Extract resource name from path"""
        # Remove leading/trailing slashes
        path = path.strip('/')
        
        # Split by slash
        parts = path.split('/')
        
        # Remove path parameters (e.g., {id})
        parts = [p for p in parts if not (p.startswith('{') and p.endswith('}'))]
        
        # Take first non-empty part as resource
        if parts:
            resource = parts[0]
        else:
            resource = 'root'
        
        # Sanitize
        return self._sanitize_name(resource)
    
    def _extract_resources_from_paths(self, paths: List[str]) -> set:
        """Extract all unique resources from paths"""
        resources = set()
        for path in paths:
            resource = self._extract_resource_from_path(path)
            resources.add(resource)
        return resources
    
    def _sanitize_name(self, name: str) -> str:
        """Sanitize name for use in scope"""
        # Convert to lowercase
        name = name.lower()
        
        # Replace spaces and special chars with underscore
        name = re.sub(r'[^a-z0-9_]', '_', name)
        
        # Remove consecutive underscores
        name = re.sub(r'_+', '_', name)
        
        # Remove leading/trailing underscores
        name = name.strip('_')
        
        return name or 'unknown'


# Singleton instance
openapi_scope_generator = OpenAPIScopeGenerator()
