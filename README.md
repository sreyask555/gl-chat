# Chat Service API

## Overview

This service provides a unified API for processing chat queries in a Goodlife shopping application. The service supports routing to different LLM models based on metadata, making it flexible for both dashboard filtering functionality and settings page assistance.

## API Design

The API follows a single-endpoint pattern:
- The `/api/chat/unified` endpoint accepts all queries, regardless of their type
- Routing to the appropriate internal handler is determined by the `metadata.page` field
- The endpoint ensures that only the necessary data (query and contextData) is passed to internal handlers
- Model configuration is handled internally by the service

## API Endpoints

### Unified Chat Endpoint

`POST /api/chat/unified`

This is the only endpoint needed for all chat functionality. It accepts a query, context data, and metadata, then routes the request to the appropriate internal handler based on the metadata.

#### Request Format

```json
{
  "query": "User's question or request",
  "contextData": {
    // Context-specific data depending on the query type
    // For dashboard queries, include:
    "availableCategories": ["Electronics", "Clothing", ...],
    "availableStores": ["Amazon", "Best Buy", ...],
    "availableLists": [{"id": "123", "name": "Wishlist"}, ...],
    "uiState": {
      "filters": {
        "categories": [],
        "stores": [],
        "lists": [],
        "timeRange": {},
        "price": {}
      },
      "viewMode": "details+image",
      "sortBy": "relevance",
      "groupBy": "none"
    },
    "lastConversation": {
      "query": "Previous user query",
      "response": "Previous assistant response"
    },
    
    // For settings queries, include:
    "profile": {
      "firstName": "John",
      "lastName": "Doe",
      "email": "john.doe@example.com"
    },
    "creditCards": {
      "userCards": [...],
      "availableCards": [...]
    },
    "memberships": [...]
  },
  "metadata": {
    "source": "webapp",
    "page": "dashboard" // or "settings"
  }
}
```

#### Response Format

For dashboard queries:
```json
{
  "response_message": "Text response to user",
  "filters": {
    "categories": ["Electronics"],
    "stores": ["Amazon"],
    "lists": [],
    "timeRange": {
      "startDate": "2023-05-01",
      "endDate": "2023-05-31",
      "label": "May 1 - May 31"
    },
    "price": {
      "min": 100,
      "max": 500
    }
  },
  "view_mode": "details+image",
  "sort_by": "price-low-high",
  "group_by": "category",
  "clear_all": false
}
```

For settings queries:
```json
{
  "generalResponse": "Text response to user about settings"
}
```

### Status Endpoint

`GET /api/chat/status`

Returns the current status of the chat service.

#### Response Format

```json
{
  "status": "ok",
  "message": "Chat service is running",
  "timestamp": "2023-05-01T12:00:00.000Z"
}
```

## Metadata Fields

The metadata object contains only information about the request's source and target page:

- `source`: The source of the request (e.g., "webapp", "mobile")
- `page`: Determines how the query is processed:
  - `dashboard` (default): Processes queries related to filtering, sorting, and organizing products on the dashboard.
  - `settings`: Processes queries related to user settings, profile, credit cards, and memberships.

## Example Usage

### Dashboard Query

```javascript
const response = await fetch('/api/chat/unified', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    query: "Show me electronics under $500",
    contextData: {
      availableCategories: ["Electronics", "Clothing", "Home"],
      // ... other context data
    },
    metadata: {
      source: "webapp",
      page: "dashboard"
    }
  })
});
```

### Settings Query

```javascript
const response = await fetch('/api/chat/unified', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    query: "What credit cards do I have?",
    contextData: {
      profile: { firstName: "John", lastName: "Doe" },
      creditCards: { userCards: [...] },
      // ... other settings data
    },
    metadata: {
      source: "webapp",
      page: "settings"
    }
  })
});
``` 