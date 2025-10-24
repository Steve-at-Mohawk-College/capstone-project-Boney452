# Flavor Quest Chat System

## 🎯 Overview

The Flavor Quest Chat System allows users to create groups, join groups, and communicate with other users in real-time. Users can discuss restaurants, share recommendations, and build a community around food discovery.

## 🏗️ Architecture

### Backend (Flask + PostgreSQL)
- **Database Tables**: `groups`, `group_members`, `messages`
- **API Endpoints**: RESTful endpoints for group and message management
- **Security**: JWT authentication, CSRF protection, input sanitization
- **Rate Limiting**: Prevents abuse and ensures fair usage

### Frontend (React)
- **ChatSystem Component**: Main chat interface
- **Real-time Updates**: Message polling (WebSocket support planned)
- **Responsive Design**: Works on desktop and mobile devices
- **Modern UI**: Glass-morphism design with smooth animations

## 📊 Database Schema

### Groups Table
```sql
CREATE TABLE groups (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    created_by INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE
);
```

### Group Members Table
```sql
CREATE TABLE group_members (
    id SERIAL PRIMARY KEY,
    group_id INTEGER NOT NULL REFERENCES groups(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    role VARCHAR(20) DEFAULT 'member' CHECK (role IN ('admin', 'member')),
    is_active BOOLEAN DEFAULT TRUE,
    UNIQUE(group_id, user_id)
);
```

### Messages Table
```sql
CREATE TABLE messages (
    id SERIAL PRIMARY KEY,
    group_id INTEGER NOT NULL REFERENCES groups(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    message_type VARCHAR(20) DEFAULT 'text' CHECK (message_type IN ('text', 'image', 'file', 'system')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_edited BOOLEAN DEFAULT FALSE,
    is_deleted BOOLEAN DEFAULT FALSE
);
```

## 🔌 API Endpoints

### Group Management

#### GET /groups
- **Description**: Get all groups the user is a member of
- **Authentication**: Required (JWT token)
- **Response**: List of groups with member count and user role

#### POST /groups
- **Description**: Create a new group
- **Authentication**: Required (JWT token)
- **CSRF Protection**: Required
- **Body**: `{ "name": "string", "description": "string" }`
- **Response**: Created group details

#### GET /groups/{id}
- **Description**: Get detailed information about a specific group
- **Authentication**: Required (JWT token)
- **Response**: Group details and member list

#### PUT /groups/{id}
- **Description**: Update group details (admin only)
- **Authentication**: Required (JWT token)
- **CSRF Protection**: Required
- **Body**: `{ "name": "string", "description": "string" }`

#### DELETE /groups/{id}
- **Description**: Delete a group (admin only)
- **Authentication**: Required (JWT token)
- **CSRF Protection**: Required

#### POST /groups/{id}/join
- **Description**: Join a group
- **Authentication**: Required (JWT token)
- **CSRF Protection**: Required

#### POST /groups/{id}/leave
- **Description**: Leave a group
- **Authentication**: Required (JWT token)
- **CSRF Protection**: Required

### Messaging

#### GET /groups/{id}/messages
- **Description**: Get messages for a specific group
- **Authentication**: Required (JWT token)
- **Query Parameters**: `page`, `limit`
- **Response**: Paginated list of messages

#### POST /groups/{id}/messages
- **Description**: Send a message to a group
- **Authentication**: Required (JWT token)
- **CSRF Protection**: Required
- **Body**: `{ "content": "string", "message_type": "text" }`

#### PUT /messages/{id}
- **Description**: Edit a message (author only)
- **Authentication**: Required (JWT token)
- **CSRF Protection**: Required
- **Body**: `{ "content": "string" }`

#### DELETE /messages/{id}
- **Description**: Delete a message (author or admin)
- **Authentication**: Required (JWT token)
- **CSRF Protection**: Required

## 🎨 Frontend Components

### ChatSystem Component
The main chat interface with three views:

1. **Groups View**: Display user's groups with options to join/leave
2. **Create Group View**: Form to create new groups
3. **Chat View**: Real-time messaging interface

### Key Features
- **Group Management**: Create, join, leave groups
- **Real-time Messaging**: Send and receive messages
- **Message History**: View past conversations
- **User Roles**: Admin and member roles with different permissions
- **Responsive Design**: Works on all device sizes

## 🔒 Security Features

### Authentication & Authorization
- JWT token-based authentication
- Role-based access control (admin/member)
- User can only access groups they're members of

### Input Validation & Sanitization
- All user inputs are sanitized to prevent XSS
- SQL injection protection through parameterized queries
- Content length limits (255 chars for group names, 2000 for messages)

### CSRF Protection
- CSRF tokens required for all state-changing operations
- Token validation with expiration

### Rate Limiting
- Group operations: 50 requests/hour
- Message operations: 100-200 requests/hour
- Prevents spam and abuse

## 🚀 Usage Guide

### For Users

#### Creating a Group
1. Click "Create Group" in the chat interface
2. Enter group name and description
3. Click "Create Group"
4. You automatically become the admin

#### Joining a Group
1. Browse available groups in "My Groups"
2. Click "Join" on any group
3. Start chatting immediately

#### Sending Messages
1. Open a group chat
2. Type your message in the input field
3. Press Enter or click "Send"
4. Messages appear in real-time

#### Managing Groups (Admin Only)
- Edit group name and description
- Delete the group (removes all members)
- Cannot leave if you're the only admin

### For Developers

#### Adding New Features
1. Update database schema if needed
2. Add backend API endpoints
3. Update frontend components
4. Test with the provided test scripts

#### Extending Message Types
1. Update the `message_type` enum in the database
2. Add validation in the backend
3. Update frontend to handle new types

## 🧪 Testing

### API Testing
Use the provided test script:
```bash
python3 test_chat_api.py
```

### Manual Testing
1. Login to the application
2. Navigate to Chat (💬 Chat button)
3. Create a test group
4. Send messages
5. Test group management features

### Database Testing
Check the sample data created by the setup script:
```bash
python3 backend/setup_chat_database.py
```

## 🔮 Future Enhancements

### Planned Features
1. **WebSocket Support**: Real-time messaging without polling
2. **File Uploads**: Share images and documents
3. **Message Reactions**: Like/react to messages
4. **Group Invitations**: Invite specific users to groups
5. **Message Search**: Search through message history
6. **Push Notifications**: Notify users of new messages
7. **Group Categories**: Organize groups by topics
8. **Message Threading**: Reply to specific messages

### Technical Improvements
1. **Caching**: Redis for frequently accessed data
2. **Message Pagination**: Infinite scroll for large conversations
3. **Offline Support**: Store messages locally when offline
4. **Message Encryption**: End-to-end encryption for sensitive groups
5. **Analytics**: Track group activity and engagement

## 📝 API Response Examples

### Get Groups Response
```json
{
  "groups": [
    {
      "id": 1,
      "name": "Food Lovers",
      "description": "A group for food enthusiasts",
      "created_by": 1,
      "created_at": "2025-10-24T10:00:00Z",
      "updated_at": "2025-10-24T10:00:00Z",
      "creator_name": "admin",
      "member_count": 5,
      "user_role": "admin"
    }
  ]
}
```

### Send Message Response
```json
{
  "message": "Message sent successfully",
  "message_data": {
    "id": 123,
    "content": "Hello everyone!",
    "message_type": "text",
    "created_at": "2025-10-24T10:30:00Z",
    "user_id": 1,
    "username": "admin"
  }
}
```

## 🐛 Troubleshooting

### Common Issues

#### "You are not a member of this group"
- User needs to join the group first
- Check if the group exists and is active

#### "Only group admins can update group details"
- User must have admin role in the group
- Check user's role in the group_members table

#### "Invalid CSRF token"
- Frontend needs to fetch a new CSRF token
- Check if the token has expired

#### Messages not appearing
- Check if user is still a member of the group
- Verify the group is active
- Check for JavaScript errors in browser console

### Debug Mode
Enable debug logging in the backend by setting:
```python
app.config['DEBUG'] = True
```

This will show detailed error messages and SQL queries.

## 📞 Support

For issues or questions about the chat system:
1. Check the troubleshooting section
2. Review the API documentation
3. Test with the provided scripts
4. Check browser console for frontend errors
5. Review backend logs for server errors
