"""Configuration management for bdnd"""

import os
import json
from pathlib import Path


def get_config_dir():
    """Get bdnd configuration directory"""
    if os.name == 'nt':  # Windows
        config_dir = Path(os.environ.get('APPDATA', os.path.expanduser('~'))) / 'bdnd'
    else:  # Linux/Mac
        config_dir = Path.home() / '.config' / 'bdnd'
    
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir


def get_config_file():
    """Get bdnd configuration file path"""
    return get_config_dir() / 'config.json'


def load_config():
    """Load bdnd configuration"""
    config_file = get_config_file()
    if config_file.exists():
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {}
    return {}


def save_config(config):
    """Save bdnd configuration"""
    config_file = get_config_file()
    try:
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        return True
    except IOError:
        return False


def get_base_path():
    """Get default base path from config"""
    config = load_config()
    return config.get('base_path', '/')


def set_base_path(path):
    """Set default base path in config"""
    config = load_config()
    config['base_path'] = path
    return save_config(config)


def get_access_token():
    """Get access token from config (optional, mainly from env)"""
    config = load_config()
    return config.get('access_token', None)

