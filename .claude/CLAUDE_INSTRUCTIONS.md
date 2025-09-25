# MCP Personal Assistant - Claude Project Instructions

## Overview
This project has access to a Personal Assistant MCP server that provides comprehensive productivity tools including status tracking, project management, todos, and calendar functionality.

## Available Tools

### Status Management Tools

#### `get_status`
Get current user status including location, laptop details, and permissions.
```
Example: "What's my current status?"
```

#### `update_status`
Update user information.
```
Parameters:
- name: Your name
- city: Current city
- state: Current state
- country: Current country
- laptop_os: Operating system
- laptop_model: Laptop model
- notes: Any additional notes

Example: "Update my status - I'm in San Francisco, CA using a MacBook Pro M1"
```

### Project Management Tools

#### `create_project`
Create a new project.
```
Parameters:
- name: Project name (required)
- description: Project description
- status: not_started, in_progress, on_hold, completed, cancelled
- priority: low, medium, high, urgent
- start_date: Start date (ISO format)
- end_date: End date (ISO format)
- tags: Array of tags

Example: "Create a project called Website Redesign with high priority"
```

#### `list_projects`
List all projects or filter by status.
```
Parameters:
- status: Filter by project status (optional)

Example: "Show me all active projects"
```

#### `get_project`
Get details of a specific project.
```
Parameters:
- project_id: ID of the project

Example: "Show me details of the Website Redesign project"
```

#### `update_project`
Update project information.
```
Parameters:
- project_id: ID of the project (required)
- name: New name
- description: New description
- status: New status
- priority: New priority
- progress: Progress percentage (0-100)
- notes: Additional notes

Example: "Update Website Redesign progress to 50%"
```

#### `add_project_task`
Add a task to a project.
```
Parameters:
- project_id: ID of the project (required)
- title: Task title (required)
- description: Task description
- status: todo, in_progress, done, blocked
- priority: low, medium, high, urgent
- due_date: Due date (ISO format)

Example: "Add task 'Design homepage' to Website Redesign project"
```

### Todo Management Tools

#### `create_todo`
Create a new todo/reminder.
```
Parameters:
- title: Todo title (required)
- description: Todo description
- due_date: Due date (ISO format)
- reminder_date: Reminder date (ISO format)
- priority: low, medium, high, urgent
- tags: Array of tags

Example: "Create a todo: Buy groceries, due tomorrow, high priority"
```

#### `list_todos`
List todos with optional filtering.
```
Parameters:
- completed: Filter by completion status (boolean)

Example: "Show me all pending todos"
```

#### `complete_todo`
Mark a todo as completed.
```
Parameters:
- todo_id: ID of the todo

Example: "Mark the groceries todo as completed"
```

### Calendar Tools

#### `create_calendar_event`
Create a calendar event.
```
Parameters:
- title: Event title (required)
- start_time: Start time (ISO format, required)
- end_time: End time (ISO format, required)
- description: Event description
- location: Event location
- attendees: Array of attendee names
- reminder_minutes: Reminder time in minutes before event

Example: "Schedule a team meeting tomorrow at 2 PM for 1 hour"
```

#### `list_calendar_events`
List calendar events within a date range.
```
Parameters:
- start_date: Start date for filter (ISO format)
- end_date: End date for filter (ISO format)

Example: "Show me this week's calendar events"
```

### Dashboard Tool

#### `get_dashboard`
Get a comprehensive dashboard view.
```
Example: "Show me my dashboard"
```

## Best Practices

1. **Natural Language**: Use natural language when interacting with the assistant. It will parse your request and use the appropriate tools.

2. **Context Awareness**: The assistant maintains context, so you can refer to previously mentioned projects or todos.

3. **Date Handling**: Use natural language for dates (tomorrow, next week) or ISO format (2024-12-20T14:00:00).

4. **ID Management**: When tools return IDs, the assistant will remember them for follow-up actions.

5. **Error Handling**: If something doesn't work, the assistant will explain the issue and suggest alternatives.

## Common Workflows

### Project Management Workflow
1. Create a project: "Create a new project called Mobile App Development"
2. Add tasks: "Add task 'UI Design' to Mobile App Development"
3. Update progress: "Update Mobile App Development progress to 25%"
4. Check status: "Show me the Mobile App Development project details"

### Daily Planning Workflow
1. Check dashboard: "Show me my dashboard"
2. Review todos: "What are my todos for today?"
3. Schedule time: "Block 2 hours tomorrow morning for project work"
4. Update status: "Update my status - working from home today"

### Task Management Workflow
1. Create todos: "Create a todo to review project proposals"
2. Set priorities: "Set the proposal review todo to high priority"
3. Complete tasks: "Mark the proposal review as completed"
4. Review pending: "Show me all incomplete todos"

## Resources

The assistant provides access to these resources:
- `pa://status` - Current user status
- `pa://projects` - All projects
- `pa://todos` - All todos
- `pa://calendar` - Calendar events

## Important Notes

1. **Data Persistence**: All data is stored locally in the MCP server's database.

2. **ID References**: When working with specific items, the assistant will handle ID lookups automatically.

3. **Time Zones**: All dates and times are stored in the local timezone.

4. **Status Updates**: Your status is automatically timestamped when updated.

5. **Active Projects**: Projects marked as "in_progress" appear in your active projects list.

## Troubleshooting

If you encounter issues:
1. Check if the MCP server is running
2. Verify Claude Desktop has the correct configuration
3. Restart Claude Desktop if needed
4. Ask "What's my current status?" to test connectivity

## Example Interactions

```
User: "What's on my plate today?"
Assistant: [Uses get_dashboard, list_todos, list_calendar_events to provide comprehensive overview]

User: "I need to start a new website project"
Assistant: [Uses create_project to create the project, then asks for details about tasks]

User: "Remind me to call John tomorrow at 3 PM"
Assistant: [Uses create_calendar_event to schedule the call with reminder]

User: "How's the Website Redesign project going?"
Assistant: [Uses get_project to show project details including progress and tasks]

User: "I finished the wireframes task"
Assistant: [Identifies the task and uses appropriate tool to mark it complete]
```
