import os
from dotenv import load_dotenv

load_dotenv()

# Flask
SECRET_KEY = os.getenv('SECRET_KEY', 'fallback-dev-key-change-me')

# Email
SENDER_EMAIL    = os.getenv('SENDER_EMAIL')
SENDER_PASSWORD = os.getenv('SENDER_PASSWORD')
TEAM_EMAIL      = os.getenv('TEAM_EMAIL')

# Admin
ADMIN_USERNAME = os.getenv('ADMIN_USERNAME')
ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD')

# Anthropic
ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY')

# Academy
ACADEMY_NAME = os.getenv('ACADEMY_NAME', 'Noble Wings Academy')

# CORS
ALLOWED_ORIGINS = os.getenv('ALLOWED_ORIGINS', 'http://localhost:5000').split(',')
