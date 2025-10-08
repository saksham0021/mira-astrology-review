"""
Configuration file for Flask application
"""

# Server Configuration
class Config:
    # Host options:
    # '127.0.0.1' or 'localhost' - Only accessible from this computer
    # '0.0.0.0' - Accessible from any device on the network
    HOST = '0.0.0.0'
    
    # Port number
    PORT = 5000
    
    # Debug mode (set to False in production)
    DEBUG = True
    
    # Upload settings
    UPLOAD_FOLDER = 'uploads'
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB
    ALLOWED_EXTENSIONS = {'xlsx', 'xls'}
    
    # Database
    DATABASE = 'mira_analysis.db'

# Alternative configurations
class LocalOnlyConfig(Config):
    """Only accessible from localhost"""
    HOST = '127.0.0.1'

class NetworkConfig(Config):
    """Accessible from network"""
    HOST = '0.0.0.0'

class ProductionConfig(Config):
    """Production settings"""
    DEBUG = False
    HOST = '0.0.0.0'
