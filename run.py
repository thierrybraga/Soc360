import os
from dotenv import load_dotenv

# Load environment variables first
load_dotenv()

from app import create_app

app = create_app(os.getenv('FLASK_ENV', 'development'))

if __name__ == '__main__':
    host = os.getenv('FLASK_RUN_HOST', '0.0.0.0')
    port = int(os.getenv('FLASK_RUN_PORT', 5000))
    debug = os.getenv('FLASK_DEBUG', 'True').lower() in ('true', '1', 't')
    
    print(f"Starting Open-Monitor on {host}:{port} (Debug: {debug})")
    app.run(host=host, port=port, debug=debug)
