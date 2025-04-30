---
title: Shakers API Documentation
category: developer_resources
tags: [api, integration, development, technical]
---

# Shakers API Documentation

## Introduction

The Shakers API allows developers to integrate our platform's functionality into their own applications, websites, and workflows. This documentation provides comprehensive information on available endpoints, authentication, request/response formats, and best practices for integration.

## API Overview

### Base URL

All API requests should be directed to:

```
https://api.shakers.com/v1
```

### Response Format

All responses are returned in JSON format. Successful responses follow this structure:

```json
{
  "status": "success",
  "data": {
    // Response data varies by endpoint
  },
  "meta": {
    "pagination": {
      "page": 1,
      "per_page": 20,
      "total_pages": 5,
      "total_records": 97
    }
  }
}
```

Error responses follow this structure:

```json
{
  "status": "error",
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable error message",
    "details": {
      // Additional error details when available
    }
  }
}
```

### Rate Limiting

API requests are subject to the following rate limits:

| Plan | Requests per Minute | Requests per Day |
|------|---------------------|------------------|
| Basic | 60 | 10,000 |
| Professional | 120 | 50,000 |
| Enterprise | 600 | 500,000 |

Rate limit information is included in response headers:

```
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 58
X-RateLimit-Reset: 1620000000
```

## Authentication

### API Keys

Authentication is performed using API keys passed in the request header:

```
Authorization: Bearer YOUR_API_KEY
```

To generate an API key:

1. Log in to your Shakers account
2. Navigate to Settings > API Access
3. Click "Generate New API Key"
4. Name your key and select appropriate permissions
5. Store the key securely as it cannot be viewed again

### OAuth Authentication

For applications requiring user-specific access, OAuth 2.0 is supported:

1. Register your application at https://shakers.com/developers/apps
2. Implement the OAuth 2.0 authorization flow
3. Use the received access token in your API requests

```
Authorization: Bearer OAUTH_ACCESS_TOKEN
```

## Core Resources

### Users

Users represent both clients and freelancers on the platform.

#### Retrieve Current User

```
GET /users/me
```

Response:

```json
{
  "status": "success",
  "data": {
    "id": "usr_12345",
    "email": "example@domain.com",
    "name": "Jane Smith",
    "user_type": "freelancer",
    "created_at": "2023-05-15T10:30:00Z",
    "profile": {
      "title": "Full Stack Developer",
      "hourly_rate": 75.00,
      "description": "...",
      "skills": ["javascript", "react", "node.js"]
    }
  }
}
```

#### Retrieve User by ID

```
GET /users/{user_id}
```

Response: Same format as above.

#### Search Users

```
GET /users/search?query=javascript&type=freelancer
```

Parameters:
- `query`: Search terms
- `type`: User type (freelancer, client)
- `skills`: Comma-separated skills list
- `location`: Geographic location
- `min_rate`, `max_rate`: Hourly rate range

Response:

```json
{
  "status": "success",
  "data": [
    {
      "id": "usr_12345",
      "name": "Jane Smith",
      "user_type": "freelancer",
      "profile": {
        "title": "Full Stack Developer",
        "hourly_rate": 75.00,
        "skills": ["javascript", "react", "node.js"]
      }
    },
    // Additional users...
  ],
  "meta": {
    "pagination": {
      "page": 1,
      "per_page": 20,
      "total_pages": 5,
      "total_records": 97
    }
  }
}
```

### Projects

Projects represent job postings created by clients.

#### List Projects

```
GET /projects
```

Parameters:
- `status`: Filter by status (open, in_progress, completed)
- `client_id`: Filter by client
- `category`: Filter by category
- `min_budget`, `max_budget`: Budget range

Response:

```json
{
  "status": "success",
  "data": [
    {
      "id": "prj_67890",
      "title": "E-commerce Website Development",
      "description": "...",
      "client_id": "usr_54321",
      "status": "open",
      "created_at": "2023-06-01T14:20:00Z",
      "budget": {
        "type": "fixed",
        "amount": 5000.00
      },
      "skills": ["php", "wordpress", "mysql"]
    },
    // Additional projects...
  ],
  "meta": {
    "pagination": {
      "page": 1,
      "per_page": 20,
      "total_pages": 3,
      "total_records": 42
    }
  }
}
```

#### Create Project

```
POST /projects
```

Request Body:

```json
{
  "title": "Mobile App Development",
  "description": "Develop an iOS app for inventory management",
  "budget": {
    "type": "fixed",
    "amount": 8000.00
  },
  "category": "mobile_development",
  "skills": ["swift", "ios", "firebase"],
  "deadline": "2023-09-30T00:00:00Z"
}
```

Response: Returns the created project object.

#### Retrieve Project

```
GET /projects/{project_id}
```

Response: Returns the specified project object.

#### Update Project

```
PATCH /projects/{project_id}
```

Request Body: Include only the fields to update.

Response: Returns the updated project object.

### Proposals

Proposals are submitted by freelancers in response to projects.

#### List Proposals for a Project

```
GET /projects/{project_id}/proposals
```

Response:

```json
{
  "status": "success",
  "data": [
    {
      "id": "prop_54321",
      "project_id": "prj_67890",
      "freelancer_id": "usr_12345",
      "cover_letter": "...",
      "amount": 4800.00,
      "estimated_duration": 30,
      "status": "pending",
      "created_at": "2023-06-02T09:15:00Z"
    },
    // Additional proposals...
  ],
  "meta": {
    "pagination": {
      "page": 1,
      "per_page": 20,
      "total_pages": 1,
      "total_records": 12
    }
  }
}
```

#### Create Proposal

```
POST /projects/{project_id}/proposals
```

Request Body:

```json
{
  "cover_letter": "I'm excited to work on this project...",
  "amount": 4800.00,
  "estimated_duration": 30
}
```

Response: Returns the created proposal object.

#### Update Proposal Status

```
PATCH /proposals/{proposal_id}
```

Request Body:

```json
{
  "status": "accepted"
}
```

Response: Returns the updated proposal object.

### Contracts

Contracts represent active agreements between clients and freelancers.

#### List Contracts

```
GET /contracts
```

Parameters:
- `status`: Filter by status (active, completed, terminated)
- `client_id`: Filter by client
- `freelancer_id`: Filter by freelancer

Response:

```json
{
  "status": "success",
  "data": [
    {
      "id": "cont_24680",
      "project_id": "prj_67890",
      "client_id": "usr_54321",
      "freelancer_id": "usr_12345",
      "status": "active",
      "created_at": "2023-06-10T11:00:00Z",
      "payment_terms": {
        "type": "fixed",
        "amount": 4800.00,
        "milestones": [
          {
            "id": "mil_11111",
            "title": "Initial Design",
            "amount": 1200.00,
            "due_date": "2023-06-25T00:00:00Z",
            "status": "completed"
          },
          {
            "id": "mil_22222",
            "title": "Development Phase",
            "amount": 2400.00,
            "due_date": "2023-07-25T00:00:00Z",
            "status": "in_progress"
          },
          {
            "id": "mil_33333",
            "title": "Final Delivery",
            "amount": 1200.00,
            "due_date": "2023-08-15T00:00:00Z",
            "status": "pending"
          }
        ]
      }
    },
    // Additional contracts...
  ],
  "meta": {
    "pagination": {
      "page": 1,
      "per_page": 20,
      "total_pages": 1,
      "total_records": 5
    }
  }
}
```

#### Create Contract

```
POST /projects/{project_id}/contracts
```

Request Body:

```json
{
  "freelancer_id": "usr_12345",
  "payment_terms": {
    "type": "fixed",
    "amount": 4800.00,
    "milestones": [
      {
        "title": "Initial Design",
        "amount": 1200.00,
        "due_date": "2023-06-25T00:00:00Z"
      },
      {
        "title": "Development Phase",
        "amount": 2400.00,
        "due_date": "2023-07-25T00:00:00Z"
      },
      {
        "title": "Final Delivery",
        "amount": 1200.00,
        "due_date": "2023-08-15T00:00:00Z"
      }
    ]
  }
}
```

Response: Returns the created contract object.

#### Update Milestone Status

```
PATCH /contracts/{contract_id}/milestones/{milestone_id}
```

Request Body:

```json
{
  "status": "completed"
}
```

Response: Returns the updated milestone object.

### Messages

Messages are communications between users.

#### List Conversations

```
GET /conversations
```

Response:

```json
{
  "status": "success",
  "data": [
    {
      "id": "conv_13579",
      "participants": [
        {"id": "usr_12345", "name": "Jane Smith"},
        {"id": "usr_54321", "name": "John Doe"}
      ],
      "last_message": {
        "sender_id": "usr_12345",
        "content": "I've completed the first milestone.",
        "created_at": "2023-06-15T13:45:00Z"
      },
      "unread_count": 2
    },
    // Additional conversations...
  ],
  "meta": {
    "pagination": {
      "page": 1,
      "per_page": 20,
      "total_pages": 1,
      "total_records": 3
    }
  }
}
```

#### Get Conversation Messages

```
GET /conversations/{conversation_id}/messages
```

Response:

```json
{
  "status": "success",
  "data": [
    {
      "id": "msg_24680",
      "conversation_id": "conv_13579",
      "sender_id": "usr_54321",
      "content": "How's the project coming along?",
      "created_at": "2023-06-15T13:30:00Z",
      "read_at": "2023-06-15T13:35:00Z"
    },
    {
      "id": "msg_24681",
      "conversation_id": "conv_13579",
      "sender_id": "usr_12345",
      "content": "I've completed the first milestone.",
      "created_at": "2023-06-15T13:45:00Z",
      "read_at": null
    },
    // Additional messages...
  ],
  "meta": {
    "pagination": {
      "page": 1,
      "per_page": 50,
      "total_pages": 1,
      "total_records": 2
    }
  }
}
```

#### Send Message

```
POST /conversations/{conversation_id}/messages
```

Request Body:

```json
{
  "content": "I've attached the updated designs."
}
```

Response: Returns the sent message object.

### Payments

Payments represent financial transactions on the platform.

#### List Payments

```
GET /payments
```

Parameters:
- `status`: Filter by status (pending, completed, failed)
- `contract_id`: Filter by contract
- `type`: Filter by type (escrow, release, refund)

Response:

```json
{
  "status": "success",
  "data": [
    {
      "id": "pmt_97531",
      "contract_id": "cont_24680",
      "milestone_id": "mil_11111",
      "amount": 1200.00,
      "currency": "USD",
      "status": "completed",
      "type": "release",
      "created_at": "2023-06-26T10:15:00Z",
      "completed_at": "2023-06-26T10:20:00Z"
    },
    // Additional payments...
  ],
  "meta": {
    "pagination": {
      "page": 1,
      "per_page": 20,
      "total_pages": 1,
      "total_records": 8
    }
  }
}
```

#### Create Payment

```
POST /payments
```

Request Body:

```json
{
  "contract_id": "cont_24680",
  "milestone_id": "mil_22222",
  "amount": 2400.00,
  "type": "release"
}
```

Response: Returns the created payment object.

## Webhooks

Webhooks allow you to receive real-time notifications about events on the Shakers platform.

### Available Events

- `user.created`
- `project.created`
- `project.updated`
- `proposal.submitted`
- `proposal.accepted`
- `contract.created`
- `contract.milestone_completed`
- `payment.completed`
- `message.sent`

### Setting Up Webhooks

1. Go to Settings > Developer > Webhooks in your Shakers account
2. Click "Add Webhook"
3. Enter the URL where you want to receive event notifications
4. Select the events you want to subscribe to
5. Set a secret key for signature verification

### Webhook Payload

Webhook notifications are sent as HTTP POST requests with the following format:

```json
{
  "event": "contract.milestone_completed",
  "timestamp": "2023-06-26T10:20:00Z",
  "data": {
    // Event-specific data
  }
}
```

Each request includes a signature in the `X-Shakers-Signature` header for verification.

### Verifying Webhook Signatures

To verify the authenticity of webhook requests, compare the signature in the header with a computed HMAC of the request body:

```python
import hmac
import hashlib

def verify_webhook(payload, signature, secret):
    computed_signature = hmac.new(
        secret.encode(),
        payload.encode(),
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(computed_signature, signature)
```

## Error Codes

| Code | Description |
|------|-------------|
| `authentication_error` | Invalid or missing API key |
| `authorization_error` | Insufficient permissions for the requested operation |
| `invalid_request` | Malformed request or invalid parameters |
| `resource_not_found` | The requested resource does not exist |
| `rate_limit_exceeded` | Too many requests in a given time period |
| `validation_error` | Request data failed validation checks |
| `internal_error` | An internal server error occurred |

## Best Practices

### Performance Optimization

- Use pagination for listing endpoints
- Request only the data you need using field selectors
- Cache responses when appropriate
- Use webhooks for real-time updates instead of polling

### Security Recommendations

- Keep API keys secure and never expose them in client-side code
- Implement HTTPS for all API communications
- Use the minimum required permissions for API keys
- Rotate API keys periodically
- Validate and sanitize all user inputs

### Rate Limit Management

- Implement exponential backoff for retry attempts
- Monitor your usage with the rate limit headers
- Distribute requests evenly rather than in bursts
- Consider upgrading your plan if you consistently approach limits

## Changelog

### v1.2 (2023-06-01)

- Added contract milestone endpoints
- Improved search functionality
- Added webhook support for message events

### v1.1 (2023-03-15)

- Added file upload endpoints
- Enhanced user search capabilities
- Improved error reporting

### v1.0 (2023-01-10)

- Initial API release

## Support

For API support and questions:

- Developer documentation: https://developers.shakers.com
- Email: api-support@shakers.example.com
- Developer community: https://community.shakers.com
