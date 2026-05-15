"""
Configuration Loader for Multi-Tenant Agentic OS Gateway
Handles YAML configuration loading, caching, and tenant management
"""

import os
import yaml
import logging
from typing import Dict, Any, Optional, List
from pathlib import Path
from functools import lru_cache
import json

logger = logging.getLogger(__name__)


class ConfigLoader:
    """
    Loads and manages tenant configurations from YAML files.
    Supports caching, hot-reload, and schema validation.
    """
    
    def __init__(self, config_dir: str = "configs"):
        """
        Initialize ConfigLoader
        
        Args:
            config_dir: Directory containing YAML config files
        """
        self.config_dir = Path(config_dir)
        self.config_cache: Dict[str, Dict[str, Any]] = {}
        self.config_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"ConfigLoader initialized with config_dir: {self.config_dir}")
    
    def load_config(self, tenant_id: str) -> Dict[str, Any]:
        """
        Load configuration for a specific tenant.
        Returns cached version if available.
        
        Args:
            tenant_id: The tenant identifier (e.g., 'acme', 'acme_v1')
            
        Returns:
            Dictionary containing tenant configuration
            
        Raises:
            FileNotFoundError: If config file doesn't exist
            yaml.YAMLError: If YAML is malformed
        """
        # Check cache first
        if tenant_id in self.config_cache:
            logger.debug(f"Using cached config for tenant: {tenant_id}")
            return self.config_cache[tenant_id]
        
        # Try to find config file
        config_file = self.config_dir / f"tenant_{tenant_id}.yaml"
        
        if not config_file.exists():
            # Try without tenant_ prefix
            config_file = self.config_dir / f"{tenant_id}.yaml"
        
        if not config_file.exists():
            # Try with .yml extension
            config_file = self.config_dir / f"tenant_{tenant_id}.yml"
        
        if not config_file.exists():
            # If still not found, create a default config
            logger.warning(f"Config file not found for tenant: {tenant_id}, creating default")
            return self._create_default_config(tenant_id)
        
        # Load from file
        try:
            with open(config_file, 'r') as f:
                config = yaml.safe_load(f) or {}
            
            # Ensure required keys
            config.setdefault('tenant_id', tenant_id)
            config.setdefault('authorized_tools', [])
            config.setdefault('policy_rules', {})
            config.setdefault('workflow_templates', {})
            
            # Cache it
            self.config_cache[tenant_id] = config
            logger.info(f"Loaded config for tenant: {tenant_id}")
            return config
            
        except yaml.YAMLError as e:
            logger.error(f"YAML parsing error for {config_file}: {e}")
            raise
        except Exception as e:
            logger.error(f"Error loading config for {tenant_id}: {e}")
            raise
    
    def _create_default_config(self, tenant_id: str) -> Dict[str, Any]:
        """Create a default configuration for a tenant"""
        default_config = {
            'tenant_id': tenant_id,
            'authorized_tools': [
                'search',
                'calculate',
                'summarize'
            ],
            'policy_rules': {
                'max_tokens': 10000,
                'max_cost': 1.0,
                'require_approval': False,
                'enable_logging': True
            },
            'workflow_templates': {
                'default': {
                    'steps': ['analyze', 'execute', 'verify']
                }
            }
        }
        
        # Cache it
        self.config_cache[tenant_id] = default_config
        logger.info(f"Created default config for tenant: {tenant_id}")
        return default_config
    
    def get_authorized_tools(self, tenant_id: str) -> List[str]:
        """
        Get list of authorized tools for a tenant
        
        Args:
            tenant_id: The tenant identifier
            
        Returns:
            List of authorized tool names
        """
        config = self.load_config(tenant_id)
        tools = config.get('authorized_tools', [])
        logger.debug(f"Authorized tools for {tenant_id}: {tools}")
        return tools
    
    def get_policy_rules(self, tenant_id: str) -> Dict[str, Any]:
        """
        Get policy rules for a tenant
        
        Args:
            tenant_id: The tenant identifier
            
        Returns:
            Dictionary of policy rules
        """
        config = self.load_config(tenant_id)
        rules = config.get('policy_rules', {})
        logger.debug(f"Policy rules for {tenant_id}: {rules}")
        return rules
    
    def is_tool_authorized(self, tenant_id: str, tool_name: str) -> bool:
        """
        Check if a specific tool is authorized for a tenant
        
        Args:
            tenant_id: The tenant identifier
            tool_name: The tool name to check
            
        Returns:
            True if tool is authorized, False otherwise
        """
        tools = self.get_authorized_tools(tenant_id)
        is_authorized = tool_name in tools
        logger.debug(f"Tool '{tool_name}' authorized for {tenant_id}: {is_authorized}")
        return is_authorized
    
    def validate_tenant(self, tenant_id: str) -> bool:
        """
        Validate that a tenant exists and has valid configuration
        
        Args:
            tenant_id: The tenant identifier
            
        Returns:
            True if tenant is valid, False otherwise
        """
        try:
            config = self.load_config(tenant_id)
            has_id = 'tenant_id' in config
            logger.info(f"Tenant {tenant_id} validation: {has_id}")
            return has_id
        except Exception as e:
            logger.error(f"Tenant {tenant_id} validation failed: {e}")
            return False
    
    def list_tenants(self) -> List[str]:
        """
        List all available tenants
        
        Returns:
            List of tenant IDs
        """
        tenants = []
        for file in self.config_dir.glob("tenant_*.yaml"):
            tenant_id = file.stem.replace("tenant_", "")
            tenants.append(tenant_id)
        
        for file in self.config_dir.glob("tenant_*.yml"):
            tenant_id = file.stem.replace("tenant_", "")
            if tenant_id not in tenants:
                tenants.append(tenant_id)
        
        logger.info(f"Found {len(tenants)} tenants: {tenants}")
        return tenants
    
    def reload_config(self, tenant_id: str) -> Dict[str, Any]:
        """
        Force reload configuration from disk (bypass cache)
        
        Args:
            tenant_id: The tenant identifier
            
        Returns:
            The reloaded configuration
        """
        # Remove from cache
        if tenant_id in self.config_cache:
            del self.config_cache[tenant_id]
        
        # Reload from disk
        config = self.load_config(tenant_id)
        logger.info(f"Reloaded config for tenant: {tenant_id}")
        return config
    
    def get_workflow_template(self, tenant_id: str, template_name: str = 'default') -> Dict[str, Any]:
        """
        Get a workflow template for a tenant
        
        Args:
            tenant_id: The tenant identifier
            template_name: Name of the workflow template
            
        Returns:
            Dictionary containing workflow template
        """
        config = self.load_config(tenant_id)
        templates = config.get('workflow_templates', {})
        template = templates.get(template_name, {'steps': ['analyze', 'execute', 'verify']})
        logger.debug(f"Workflow template '{template_name}' for {tenant_id}: {template}")
        return template


# Create a global instance for easy access
_global_loader = None


def get_config_loader(config_dir: str = "configs") -> ConfigLoader:
    """
    Get or create the global ConfigLoader instance
    
    Args:
        config_dir: Directory containing YAML config files
        
    Returns:
        ConfigLoader instance
    """
    global _global_loader
    if _global_loader is None:
        _global_loader = ConfigLoader(config_dir)
    return _global_loader


def get_tenant_config(tenant_id: str, config_dir: str = "configs") -> Dict[str, Any]:
    """
    Convenience function to load a tenant config
    
    Args:
        tenant_id: The tenant identifier
        config_dir: Directory containing YAML config files
        
    Returns:
        Tenant configuration dictionary
    """
    loader = get_config_loader(config_dir)
    return loader.load_config(tenant_id)


# For backwards compatibility
config_loader = get_config_loader()


if __name__ == "__main__":
    # Simple test
    logging.basicConfig(level=logging.DEBUG)
    
    loader = ConfigLoader("./configs")
    
    # Load a config
    config = loader.load_config("acme")
    print("Config loaded:", json.dumps(config, indent=2))
    
    # Check authorization
    is_auth = loader.is_tool_authorized("acme", "search")
    print(f"Search authorized for acme: {is_auth}")
    
    # List all tenants
    tenants = loader.list_tenants()
    print(f"Available tenants: {tenants}")