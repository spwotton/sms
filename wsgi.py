"""
WSGI entry point for production deployment

This module creates the Flask application instance for WSGI servers like gunicorn.
"""
import os
from app import create_app

# Get configuration from environment
config_name = os.getenv('FLASK_ENV', 'production')

# Create application instance
app = create_app(config_name)

if __name__ == "__main__":
    # For development purposes only
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
