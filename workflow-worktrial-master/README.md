# Interaction Logger Chrome Extension

A Chrome extension that tracks user interactions on web pages and sends them to an API endpoint.

## Overview

This extension captures user interactions (clicks, typing, copy/paste, highlights, tab switches) and page content in markdown format, then allows sending these events to a configurable API endpoint.

## Features

- 📊 **Interaction Tracking**: Captures clicks, typing, copy/paste, text selection, tab switches
- 📄 **Page Content**: Converts pages to markdown on load using TurndownService
- 💾 **Smart Storage**: Configurable ring buffer + browser storage persistence
- 🔍 **Detailed Logging**: Console logs with tab/window IDs for debugging
- 📤 **API Export**: Send configurable number of interactions to your API endpoint

## Project Structure

```
wxt-dev-wxt/
├── entrypoints/
│   ├── background.ts           # Background service worker
│   ├── background/
│   │   └── interactionManager.ts # Core event handling & storage
│   ├── content.ts              # Content script entry point
│   ├── content/
│   │   ├── interactionLogger.ts  # DOM event listeners
│   │   └── pageConverter.ts      # HTML to Markdown conversion
│   ├── popup/
│   │   └── App.tsx             # Popup UI with event display
│   ├── types/
│   │   └── interactions.ts     # TypeScript interfaces
│   └── config.ts               # Centralized configuration
├── tools-dump/                 # Integration tool definitions
│   ├── discord.txt            # Discord API tools
│   ├── gmail.txt              # Gmail operations
│   ├── github.txt             # GitHub management
│   └── ...                    # Other service integrations
├── .env                        # API endpoint configuration
├── wxt.config.ts              # Extension manifest config
└── package.json
```

## File Descriptions

### Core Files

- **`background/interactionManager.ts`**: Manages all interaction events
  - Ring buffer for memory management (configurable size via .env)
  - Tab lifecycle tracking (activation, removal, navigation)
  - Storage persistence with `ev:` prefixed keys
  - Message passing between content and popup

- **`content/interactionLogger.ts`**: Captures DOM interactions
  - Event listeners for clicks, typing, copy/paste, selections
  - Detects interactive elements (buttons, links, inputs)
  - Sends events to background script

- **`content/pageConverter.ts`**: Converts HTML to Markdown
  - Uses TurndownService for conversion
  - Removes code blocks and hidden elements
  - Caches markdown for 2 seconds to avoid regeneration

- **`popup/App.tsx`**: User interface
  - Displays interaction count and details
  - Shows tab/window IDs for each event
  - Sends interactions to API endpoint
  - Auto-refreshes every 5 seconds

## Setup

1. Install dependencies:
```bash
npm install
```

2. Configure settings in `.env`:
```bash
# API endpoint for sending interactions
VITE_API_ENDPOINT=http://localhost:3000/api/interactions

# Ring buffer size (max events stored in memory per buffer)
VITE_RING_BUFFER_SIZE=2000

# Number of interactions to send to API (should be <= buffer size)
VITE_API_EXPORT_SIZE=1000
```

3. Start development server:
```bash
npx wxt --port 3001
```

## Usage

1. **Browse normally** - The extension tracks interactions automatically
2. **Click extension icon** - Opens popup showing interaction count
3. **View details** - Click "Show Details" to see recent events
4. **Send to API** - Click "Send X Interactions" to POST to your endpoint

## API Format

The extension sends a POST request with:

```json
{
  "events": [
    {
      "id": "uuid",
      "type": "click|type|copy|paste|highlight|page-load|tab-switch",
      "timestamp": 1234567890,
      "tabId": 42,
      "windowId": 1,
      "url": "https://example.com",
      "title": "Page Title",
      "payload": {
        // Event-specific data
        "markdown": "..." // For page-load events
      }
    }
  ],
  "timestamp": 1234567890
}
```

## Event Types

- **`page-load`**: New page loaded (includes markdown content)
- **`click`**: Interactive element clicked
- **`type`**: Text input changed
- **`copy`**: Text copied
- **`paste`**: Text pasted
- **`highlight`**: Text selected
- **`tab-switch`**: Active tab changed
- **`tab-removal`**: Tab closed

## Debugging

Check console logs in:
- **Content Script**: Page DevTools console (`[Content]` prefix)
- **Background**: Extension service worker (`[Background]` prefix)
- **Popup**: Extension popup DevTools

## Tools Directory (`tools-dump/`)

The `tools-dump/` directory contains integration tool definitions for various services. These are used for workflow suggestions based on user interactions.

### Available Integrations

- **discord.txt** - Discord messaging tools
- **github.txt** - GitHub repository management
- **gmail.txt** - Gmail email operations
- **google_calendar.txt** - Google Calendar events
- **google_docs.txt** - Google Docs operations
- **google_drive.txt** - Google Drive file management
- **google_sheets.txt** - Google Sheets operations
- **hubspot.txt** - HubSpot CRM tools
- **jira.txt** - Jira issue tracking
- **linear.txt** - Linear issue management
- **microsoft_outlook.txt** - Outlook email/calendar
- **microsoft_teams.txt** - Teams collaboration
- **notion.txt** - Notion workspace tools
- **reddit.txt** - Reddit API operations
- **slack.txt** - Slack messaging

### Tool Definition Structure

Each tool is defined as a JSON object (one per line) with the following structure:

```json
{
  "name": "tool-unique-identifier",
  "label": "Human Readable Name",
  "description": "What this tool does and documentation link",
  "inputSchema": {
    "jsonSchema": {
      "type": "object",
      "properties": {
        "paramName": {
          "type": "string|boolean|array|etc",
          "description": "Parameter description"
        }
      },
      "required": ["requiredParam1", "requiredParam2"],
      "additionalProperties": false,
      "$schema": "http://json-schema.org/draft-07/schema#"
    }
  }
}
```

### Example Tool Entry

```json
{
  "name": "gmail-find-email",
  "label": "Find Email",
  "description": "Find an email using Google's Search Engine",
  "inputSchema": {
    "jsonSchema": {
      "type": "object",
      "properties": {
        "q": {
          "type": "string",
          "description": "Apply a search filter using Gmail search syntax"
        }
      }
    }
  }
}
```

## Development

Built with:
- [WXT](https://wxt.dev/) - Extension framework
- React - Popup UI
- TurndownService - HTML to Markdown conversion
- TypeScript - Type safety