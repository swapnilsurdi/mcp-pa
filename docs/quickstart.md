# MCP Personal Assistant - Quick Start Guide

## 🚀 Installation (5 minutes)

1. **Run the setup script:**

   ```bash
   cd /Users/surdi/Documents/mcp-pa
   python setup.py
   ```

2. **Configure Claude Desktop:**
   Add this to your Claude Desktop config file:

   ```json
   {
     "mcpServers": {
       "personal-assistant": {
         "command": "python",
         "args": ["-m", "src.server"],
         "cwd": "/Users/surdi/Documents/mcp-pa",
         "env": {
           "MCP_PA_DB_TYPE": "sqlite",
           "MCP_PA_ENCRYPTION_KEY": "optional-secret-key"
         }
       }
     }
   }
   ```

   Location: `~/Library/Application Support/Claude/claude_desktop_config.json`

3. **Restart Claude Desktop**

## 🎯 First Time Usage

Try these commands in Claude to get started:

1. **Check your status:**
   "What's my current status?"

2. **Update your information:**
   "Update my status - I'm Swapnil, currently in San Jose, CA, using a Mac Mini"

3. **Create your first project:**
   "Create a new project called 'Personal Website' with high priority"

4. **Add a task:**
   "Add a task to Personal Website: Design the homepage"

5. **Create a todo:**
   "Create a todo: Review project progress - due tomorrow"

6. **Schedule an event:**
   "Schedule a meeting: Team sync - tomorrow at 2 PM for 1 hour"

7. **Upload a document:**
   "I have a document to store" (then provide the file)

8. **View your dashboard:**
   "Show me my dashboard"

## 📚 Common Commands

### Status Management

- "What's my current status?"
- "Update my location to San Francisco, CA"
- "Update my laptop details - MacBook Pro M1 with macOS Sonoma"

### Project Management

- "Create a project called [name]"
- "List all my projects"
- "Show me active projects"
- "Update [project name] progress to 50%"
- "Add a task to [project name]: [task description]"

### Todo Management

- "Create a todo: [description] due [date]"
- "Show me all pending todos"
- "Mark [todo name] as completed"
- "List todos due this week"

### Calendar Management

- "Schedule a meeting: [title] on [date] at [time]"
- "Show me this week's events"
- "Create an event: [title] from [start time] to [end time]"

### Document Management

- "Store this document" (provide file)
- "Create a reference to this Google Doc: [URL]"
- "Show me all my documents"
- "List documents tagged with 'finance'"

### Dashboard

- "Show me my dashboard"
- "What's my current workload?"
- "Give me an overview of my projects and tasks"

## 🔧 Configuration Options

Set these environment variables before starting:

```bash
# Choose database type (sqlite or tinydb)
export MCP_PA_DB_TYPE=sqlite

# Set encryption key (optional but recommended)
export MCP_PA_ENCRYPTION_KEY=your-secret-key

# Custom document storage location
export MCP_PA_DOCS_DIR=/path/to/documents

# Maximum file size in MB
export MCP_PA_MAX_FILE_SIZE_MB=100
```

## 🔍 Need Help?

Check the [README.md](README.md) for detailed documentation on all available features and tools.
