import subprocess
import sys
import os

def install_requirements():
    """Install required packages."""
    print("Installing requirements...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])

def run_app():
    """Run the FastAPI application."""
    print("Starting 52-Week Dash application...")
    subprocess.run([sys.executable, "-m", "uvicorn", "app.api.main:app", "--host", "127.0.0.1", "--port", "8000", "--reload"])

if __name__ == "__main__":
    try:
        install_requirements()
        run_app()
    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1) 