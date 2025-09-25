# Examples

This directory contains examples and templates for using the MCP Personal Assistant.

## Files

### `claude_desktop_config.json`
Template configuration for Claude Desktop. Copy this to your Claude Desktop configuration directory and update the paths:

- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Linux**: `~/.config/Claude/claude_desktop_config.json`
- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

**Important**: Update the `/path/to/your/mcp-pa` placeholders with your actual project path.

### `basic_usage.py`
Standalone Python script demonstrating how to use the MCP Personal Assistant API directly, without Claude Desktop. This is useful for:

- Testing the functionality
- Understanding the API
- Development and debugging
- Automated scripts

Run it with:
```bash
cd /path/to/mcp-pa
source venv/bin/activate
python examples/basic_usage.py
```

## Quick Setup

1. **Copy the Claude Desktop config**:
   ```bash
   cp examples/claude_desktop_config.json ~/Library/Application\ Support/Claude/claude_desktop_config.json
   ```

2. **Edit the paths in the config file** to match your setup

3. **Restart Claude Desktop**

4. **Test with the basic usage script**:
   ```bash
   python examples/basic_usage.py
   ```