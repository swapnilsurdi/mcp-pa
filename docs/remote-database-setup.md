# Remote Database Setup Guide

This guide shows how to configure the MCP Personal Assistant to use a remote database instead of a local SQLite file.

## Why Use a Remote Database?

- **Multi-device sync**: Access your data from multiple computers
- **Backup & reliability**: Professional database hosting with automated backups
- **Scalability**: Better performance for large datasets
- **Collaboration**: Share data across team members (future feature)

## Option 1: PostgreSQL (Recommended)

### Supported Services

- **Supabase** (Free tier available, easiest setup)
- **AWS RDS** (Enterprise-grade)
- **Google Cloud SQL**
- **Azure Database for PostgreSQL**
- **PlanetScale** (MySQL-compatible)
- **Neon** (Serverless PostgreSQL)

### Setup Instructions

#### 1. Install PostgreSQL Dependencies

```bash
cd /path/to/your/mcp-pa
source venv/bin/activate
pip install asyncpg psycopg2-binary
```

#### 2. Create Database (Supabase Example)

1. Go to [supabase.com](https://supabase.com) and create an account
2. Create a new project
3. Go to Settings > Database
4. Copy your connection string (it looks like):
   ```
   postgresql://postgres:[YOUR-PASSWORD]@db.[YOUR-PROJECT].supabase.co:5432/postgres
   ```

#### 3. Update Claude Desktop Configuration

Replace your `claude_desktop_config.json` with:

```json
{
  "mcpServers": {
    "personal-assistant": {
      "command": "/path/to/your/mcp-pa/venv/bin/python",
      "args": ["-m", "src.server"],
      "cwd": "/path/to/your/mcp-pa",
      "env": {
        "MCP_PA_DB_TYPE": "postgresql",
        "MCP_PA_PGVECTOR_CONNECTION_STRING": "postgresql://postgres:YOUR-PASSWORD@db.YOUR-PROJECT.supabase.co:5432/postgres"
      }
    }
  }
}
```

#### 4. Test the Connection

```bash
source venv/bin/activate
python examples/basic_usage.py
```

If successful, your data is now stored in the remote PostgreSQL database!

### Advanced PostgreSQL Features

The PostgreSQL backend includes:

- **Vector embeddings**: For semantic search (future feature)
- **Full-text search**: Across documents and projects
- **JSONB fields**: For flexible metadata storage
- **Concurrent access**: Multiple users/devices simultaneously
- **Transactions**: Data integrity guarantees

## Option 2: Cloud-Synced SQLite (Simple)

If you prefer to keep using SQLite but want cross-device sync:

### Using Cloud Storage

```json
{
  "mcpServers": {
    "personal-assistant": {
      "command": "/path/to/your/mcp-pa/venv/bin/python",
      "args": ["-m", "src.server"],
      "cwd": "/path/to/your/mcp-pa",
      "env": {
        "MCP_PA_DB_TYPE": "sqlite",
        "MCP_PA_DB_PATH": "/Users/your-name/Dropbox/mcp-pa/database.sqlite"
      }
    }
  }
}
```

**Supported cloud storage:**
- Dropbox: `/Users/your-name/Dropbox/mcp-pa/`
- iCloud: `/Users/your-name/Library/Mobile Documents/com~apple~CloudDocs/mcp-pa/`
- Google Drive: `/Users/your-name/Google Drive/mcp-pa/`

⚠️ **Note**: SQLite with cloud sync can have conflicts if accessed simultaneously from multiple devices.

## Connection String Examples

### PostgreSQL Formats

```bash
# Supabase
postgresql://postgres:password@db.project.supabase.co:5432/postgres

# AWS RDS
postgresql://username:password@mydb.cluster-xxx.us-east-1.rds.amazonaws.com:5432/mcppa

# Google Cloud SQL
postgresql://username:password@127.0.0.1:5432/mcppa?host=/cloudsql/project:region:instance

# Local PostgreSQL
postgresql://postgres:password@localhost:5432/mcp_personal_assistant

# With SSL (recommended for production)
postgresql://user:pass@host:5432/db?sslmode=require
```

## Environment Variables

You can also set these as environment variables instead of in the config:

```bash
export MCP_PA_DB_TYPE=postgresql
export MCP_PA_PGVECTOR_CONNECTION_STRING="postgresql://postgres:password@host:5432/db"

# Then use in Claude Desktop config:
{
  "mcpServers": {
    "personal-assistant": {
      "command": "/path/to/your/mcp-pa/venv/bin/python",
      "args": ["-m", "src.server"],
      "cwd": "/path/to/your/mcp-pa"
    }
  }
}
```

## Migration from SQLite

To migrate your existing SQLite data to PostgreSQL:

1. **Export your SQLite data:**
   ```bash
   source venv/bin/activate
   python scripts/export_data.py --format json --output backup.json
   ```

2. **Switch to PostgreSQL** (follow setup above)

3. **Import your data:**
   ```bash
   python scripts/import_data.py --format json --input backup.json
   ```

*Note: Migration scripts need to be created if not already available.*

## Troubleshooting

### Connection Issues

1. **Check firewall settings** - ensure port 5432 is accessible
2. **Verify connection string** - test with psql command-line tool
3. **Check SSL requirements** - some hosts require `sslmode=require`

### Performance Tips

1. **Connection pooling** is automatically handled
2. **Indexes** are created automatically for common queries
3. **Consider read replicas** for high-traffic scenarios

### Security Best Practices

1. **Use environment variables** for credentials (not config files)
2. **Enable SSL/TLS** for production databases
3. **Restrict IP access** in your database hosting settings
4. **Use strong passwords** and rotate them regularly

## Cost Considerations

- **Supabase**: Free tier (500MB), then ~$25/month
- **AWS RDS**: ~$15-30/month for small instances
- **Google Cloud SQL**: ~$10-25/month for basic setup
- **Neon**: Generous free tier, serverless pricing

The SQLite + cloud storage option costs just the price of your cloud storage plan.