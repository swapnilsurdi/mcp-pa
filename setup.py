#!/usr/bin/env python3
"""
Setup script for MCP Personal Assistant
"""

import os
import sys
import subprocess
import json
import shutil

def run_command(command):
    """Run a command and capture output"""
    try:
        result = subprocess.run(command, shell=True, check=True, text=True, capture_output=True)
        print(f"✓ {command}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to run: {command}")
        print(f"Error: {e.stderr}")
        return False

def setup_virtual_environment():
    """Create and activate a virtual environment"""
    print("\n🔧 Setting up virtual environment...")
    
    if not run_command(f"{sys.executable} -m venv venv"):
        return False
    
    # Determine the correct activation command based on OS
    if sys.platform == "win32":
        activate_cmd = "venv\\Scripts\\activate"
        pip_cmd = "venv\\Scripts\\pip"
    else:
        activate_cmd = "source venv/bin/activate"
        pip_cmd = "venv/bin/pip"
    
    print(f"ℹ️  To activate the virtual environment, run: {activate_cmd}")
    return pip_cmd

def install_dependencies(pip_cmd):
    """Install required dependencies"""
    print("\n📦 Installing dependencies...")
    return run_command(f"{pip_cmd} install -r requirements.txt")

def create_directories():
    """Create necessary directories"""
    print("\n📁 Creating directories...")
    
    directories = [
        "data",
    ]
    
    # Add OS-specific directories
    if sys.platform == "darwin":  # macOS
        directories.extend([
            os.path.expanduser("~/Library/Application Support/mcp-pa"),
            os.path.expanduser("~/Library/Application Support/mcp-pa/documents"),
        ])
    elif sys.platform == "win32":  # Windows
        directories.extend([
            os.path.expandvars("%APPDATA%\\mcp-pa"),
            os.path.expandvars("%APPDATA%\\mcp-pa\\documents"),
        ])
    else:  # Linux
        directories.extend([
            os.path.expanduser("~/.config/mcp-pa"),
            os.path.expanduser("~/.config/mcp-pa/documents"),
        ])
    
    try:
        for directory in directories:
            os.makedirs(directory, exist_ok=True)
            print(f"✓ Created directory: {directory}")
        return True
    except Exception as e:
        print(f"❌ Failed to create directories: {e}")
        return False

def test_installation(pip_cmd):
    """Run test script to verify installation"""
    print("\n🧪 Testing installation...")
    
    # Use the virtual environment's Python
    if sys.platform == "win32":
        python_cmd = "venv\\Scripts\\python"
    else:
        python_cmd = "venv/bin/python"
    
    return run_command(f"{python_cmd} test_server.py")

def setup_claude_desktop_config():
    """Help setup Claude Desktop configuration"""
    print("\n🔧 Claude Desktop Configuration")
    print("=" * 50)
    print("To use this MCP server with Claude Desktop, add the following to your config file:")
    print()
    
    config = {
        "mcpServers": {
            "personal-assistant": {
                "command": "python",
                "args": ["-m", "src.server"],
                "cwd": os.path.abspath("."),
                "env": {
                    "MCP_PA_DB_TYPE": "sqlite",
                    "MCP_PA_ENCRYPTION_KEY": "optional-secret-key-here"
                }
            }
        }
    }
    
    print(json.dumps(config, indent=2))
    print()
    print("Configuration file location:")
    if sys.platform == "darwin":  # macOS
        print("~/Library/Application Support/Claude/claude_desktop_config.json")
    elif sys.platform == "win32":  # Windows
        print("%APPDATA%\\Claude\\claude_desktop_config.json")
    else:  # Linux
        print("~/.config/Claude/claude_desktop_config.json")
    
    print("\nOptional environment variables:")
    print("- MCP_PA_DB_TYPE: 'sqlite' or 'tinydb' (default: sqlite)")
    print("- MCP_PA_ENCRYPTION_KEY: Your encryption key for secure storage")
    print("- MCP_PA_DOCS_DIR: Custom directory for document storage")
    print("- MCP_PA_MAX_FILE_SIZE_MB: Maximum file size in MB (default: 100)")

def main():
    print("🚀 MCP Personal Assistant Setup")
    print("=" * 50)
    
    # Check Python version
    if sys.version_info < (3, 10):
        print("❌ Error: Python 3.10 or higher is required")
        sys.exit(1)
    
    # Setup virtual environment
    pip_cmd = setup_virtual_environment()
    if not pip_cmd:
        print("❌ Failed to setup virtual environment")
        sys.exit(1)
    
    # Install dependencies
    if not install_dependencies(pip_cmd):
        print("❌ Failed to install dependencies")
        sys.exit(1)
    
    # Create directories
    if not create_directories():
        print("❌ Failed to create directories")
        sys.exit(1)
    
    # Test installation
    if not test_installation(pip_cmd):
        print("❌ Installation test failed")
        sys.exit(1)
    
    # Show Claude Desktop configuration
    setup_claude_desktop_config()
    
    print("\n✅ Setup completed successfully!")
    print("\nNext steps:")
    print("1. Configure Claude Desktop with the settings above")
    print("2. Restart Claude Desktop")
    print("3. Start using the Personal Assistant!")
    print("\nTo start the server manually, run:")
    if sys.platform == "win32":
        print("venv\\Scripts\\python -m src.server")
    else:
        print("source venv/bin/activate && python -m src.server")
    
    print("\nFor detailed configuration options, see docs/CONFIGURATION.md")

if __name__ == "__main__":
    main()
