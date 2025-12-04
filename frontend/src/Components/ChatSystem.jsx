import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { sanitizeInput, csrfManager, containsInappropriateContent } from '../utils/security';
import { API_BASE_URL } from '../config';
import { tokenStorage } from '../utils/tokenStorage';

function ChatSystem({ userInfo, onSignOut, onBackToSearch }) {
  const [currentView, setCurrentView] = useState('groups'); // 'groups', 'chat', 'create-group', 'discover', 'edit-group'
  const [groups, setGroups] = useState([]);
  const [discoverGroups, setDiscoverGroups] = useState([]);
  const [selectedGroup, setSelectedGroup] = useState(null);
  const [messages, setMessages] = useState([]);
  const [newMessage, setNewMessage] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  // Group creation state
  const [groupName, setGroupName] = useState('');
  const [groupDescription, setGroupDescription] = useState('');

  // Group editing state
  const [editingGroup, setEditingGroup] = useState(null);
  const [editGroupName, setEditGroupName] = useState('');
  const [editGroupDescription, setEditGroupDescription] = useState('');


  useEffect(() => {
    if (userInfo) {
      loadGroups();
    } else {
      setError('Authentication required to access the chat system.');
    }
  }, [userInfo]);

  const loadGroups = async () => {
    try {
      setLoading(true);
      const token = tokenStorage.get();
      if (!token) {
        setError('Authentication required. Please sign in to continue.');
        return;
      }
      const response = await axios.get(`${API_BASE_URL}/groups`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setGroups(response.data.groups);
    } catch (error) {
      setError('Unable to load groups. Please verify your authentication and try again.');
      console.error('Load groups error:', error);
    } finally {
      setLoading(false);
    }
  };

  const loadDiscoverGroups = async () => {
    try {
      setLoading(true);
      const token = tokenStorage.get();
      if (!token) {
        setError('Authentication required. Please sign in to continue.');
        return;
      }
      const response = await axios.get(`${API_BASE_URL}/groups/discover`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setDiscoverGroups(response.data.groups);
    } catch (error) {
      setError('Unable to load available groups. Please try again later.');
      console.error('Load discover groups error:', error);
    } finally {
      setLoading(false);
    }
  };

  const loadMessages = async (groupId) => {
    try {
      setLoading(true);
      const token = tokenStorage.get();
      const response = await axios.get(`${API_BASE_URL}/groups/${groupId}/messages`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setMessages(response.data.messages.reverse()); // Reverse to show oldest first
    } catch (error) {
      setError('Unable to load messages. Please try again.');
      console.error('Load messages error:', error);
    } finally {
      setLoading(false);
    }
  };

  const createGroup = async (e) => {
    e.preventDefault();
    try {
      setLoading(true);
      setError('');
      
      const token = tokenStorage.get();
      if (!token) {
        setError('Authentication required. Please sign in to continue.');
        return;
      }
      
      const csrfToken = await csrfManager.getToken();
      
      const response = await axios.post(`${API_BASE_URL}/groups`, {
        name: sanitizeInput(groupName, 255),
        description: sanitizeInput(groupDescription, 1000)
      }, {
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
          'X-CSRF-Token': csrfToken
        }
      });

      setSuccess('Group created successfully!');
      setGroupName('');
      setGroupDescription('');
      setCurrentView('groups');
      loadGroups();
    } catch (error) {
      setError(error.response?.data?.error || 'Unable to create group. Please try again.');
      console.error('Create group error:', error);
    } finally {
      setLoading(false);
    }
  };

  const joinGroup = async (groupId) => {
    try {
      setLoading(true);
      setError('');
      
      const token = tokenStorage.get();
      const csrfToken = await csrfManager.getToken();
      
      await axios.post(`${API_BASE_URL}/groups/${groupId}/join`, {}, {
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
          'X-CSRF-Token': csrfToken
        }
      });

      setSuccess('Successfully joined the group!');
      loadGroups();
    } catch (error) {
      setError(error.response?.data?.error || 'Unable to join group. Please try again.');
      console.error('Join group error:', error);
    } finally {
      setLoading(false);
    }
  };

  const leaveGroup = async (groupId) => {
    try {
      setLoading(true);
      setError('');
      
      const token = tokenStorage.get();
      const csrfToken = await csrfManager.getToken();
      
      await axios.post(`${API_BASE_URL}/groups/${groupId}/leave`, {}, {
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
          'X-CSRF-Token': csrfToken
        }
      });

      setSuccess('Successfully left the group!');
      loadGroups();
      if (selectedGroup && selectedGroup.id === groupId) {
        setCurrentView('groups');
        setSelectedGroup(null);
      }
    } catch (error) {
      setError(error.response?.data?.error || 'Unable to leave group. Please try again.');
      console.error('Leave group error:', error);
    } finally {
      setLoading(false);
    }
  };

  const startEditGroup = (group) => {
    setEditingGroup(group);
    setEditGroupName(group.name);
    setEditGroupDescription(group.description || '');
    setCurrentView('edit-group');
    setError('');
    setSuccess('');
  };

  const cancelEditGroup = () => {
    setEditingGroup(null);
    setEditGroupName('');
    setEditGroupDescription('');
    setCurrentView('groups');
    setError('');
    setSuccess('');
  };

  const submitEditGroup = async (e) => {
    e.preventDefault();
    if (!editingGroup) return;

    try {
      setLoading(true);
      setError('');
      
      const token = tokenStorage.get();
      const csrfToken = await csrfManager.getToken();
      
      await axios.put(`${API_BASE_URL}/groups/${editingGroup.id}`, {
        name: sanitizeInput(editGroupName, 255),
        description: sanitizeInput(editGroupDescription, 1000)
      }, {
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
          'X-CSRF-Token': csrfToken
        }
      });

      setSuccess('Group updated successfully!');
      loadGroups();
      loadDiscoverGroups();
      cancelEditGroup();
    } catch (error) {
      setError(error.response?.data?.error || 'Unable to update group. Please try again.');
      console.error('Edit group error:', error);
    } finally {
      setLoading(false);
    }
  };

  const deleteGroup = async (groupId) => {
    try {
      setLoading(true);
      setError('');
      
      const token = tokenStorage.get();
      const csrfToken = await csrfManager.getToken();
      
      await axios.delete(`${API_BASE_URL}/groups/${groupId}`, {
        headers: {
          Authorization: `Bearer ${token}`,
          'X-CSRF-Token': csrfToken
        }
      });

      setSuccess('Group deleted successfully!');
      loadGroups();
      loadDiscoverGroups();
      if (selectedGroup && selectedGroup.id === groupId) {
        setCurrentView('groups');
        setSelectedGroup(null);
      }
    } catch (error) {
      setError(error.response?.data?.error || 'Unable to delete group. Please try again.');
      console.error('Delete group error:', error);
    } finally {
      setLoading(false);
    }
  };

  const sendMessage = async (e) => {
    e.preventDefault();
    if (!newMessage.trim() || !selectedGroup) return;

    // Check for inappropriate content
    if (containsInappropriateContent(newMessage)) {
      setError("Your message contains inappropriate content. Please revise your message and try again.");
      return;
    }

    try {
      setLoading(true);
      setError('');
      
      const token = tokenStorage.get();
      const csrfToken = await csrfManager.getToken();
      
      const response = await axios.post(`${API_BASE_URL}/groups/${selectedGroup.id}/messages`, {
        content: sanitizeInput(newMessage, 2000),
        message_type: 'text'
      }, {
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
          'X-CSRF-Token': csrfToken
        }
      });

      // Add the new message to the messages list
      setMessages(prev => [...prev, response.data.message_data]);
      setNewMessage('');
    } catch (error) {
      setError(error.response?.data?.error || 'Unable to send message. Please try again.');
      console.error('Send message error:', error);
    } finally {
      setLoading(false);
    }
  };

  const openChat = (group) => {
    setSelectedGroup(group);
    setCurrentView('chat');
    loadMessages(group.id);
  };

  const formatTime = (timestamp) => {
    if (!timestamp) return '';
    const date = new Date(timestamp);
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };

  const formatDate = (timestamp) => {
    if (!timestamp) return '';
    const date = new Date(timestamp);
    const today = new Date();
    const yesterday = new Date(today);
    yesterday.setDate(yesterday.getDate() - 1);

    if (date.toDateString() === today.toDateString()) {
      return 'Today';
    } else if (date.toDateString() === yesterday.toDateString()) {
      return 'Yesterday';
    } else {
      return date.toLocaleDateString();
    }
  };

  // Clear messages after 3 seconds
  useEffect(() => {
    if (error || success) {
      const timer = setTimeout(() => {
        setError('');
        setSuccess('');
      }, 3000);
      return () => clearTimeout(timer);
    }
  }, [error, success]);

  // Redirect to login if no user info
  if (!userInfo) {
    return (
      <div className="chat-system">
        <div className="chat-content">
          <div className="text-center py-8">
            <h2 className="text-xl font-semibold mb-4">Authentication Required</h2>
            <p className="text-gray-600 mb-4">Please login to access the chat system.</p>
            <button 
              onClick={onSignOut}
              className="btn btn-primary"
            >
              Go to Login
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="chat-system">
      {/* Header */}
      <div className="chat-header">
        <div className="flex items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            {typeof onBackToSearch === 'function' && (
              <button
                onClick={onBackToSearch}
                className="btn btn-ghost"
              >
                ← Back to Search
              </button>
            )}
            <h1 className="header-xl">Flavor Quest Chat</h1>
          </div>
          <button 
            onClick={onSignOut}
            className="btn btn-secondary"
          >
            Sign Out
          </button>
        </div>
      </div>

      {/* Navigation */}
      <div className="chat-nav">
        <button 
          onClick={() => setCurrentView('groups')}
          className={`nav-btn ${currentView === 'groups' ? 'active' : ''}`}
        >
          My Groups
        </button>
        <button 
          onClick={() => {
            setCurrentView('discover');
            setError('');
            setSuccess('');
            loadDiscoverGroups();
          }}
          className={`nav-btn ${currentView === 'discover' ? 'active' : ''}`}
        >
          Discover Groups
        </button>
        <button 
          onClick={() => setCurrentView('create-group')}
          className={`nav-btn ${currentView === 'create-group' ? 'active' : ''}`}
        >
          Create Group
        </button>
      </div>

      {/* Error/Success Messages */}
      {error && (
        <div 
          className="glass p-3 rounded-lg border border-red-200/70 text-red-700 text-sm mb-4"
          role="alert"
          aria-live="polite"
          aria-atomic="true"
        >
          {error}
        </div>
      )}
      {success && (
        <div 
          className="glass p-3 rounded-lg border border-green-200/70 text-green-800 text-sm mb-4"
          role="status"
          aria-live="polite"
          aria-atomic="true"
        >
          {success}
        </div>
      )}

      {/* Main Content */}
      <div className="chat-content">
        {currentView === 'groups' && (
          <div className="groups-view">
            <h2 className="text-xl font-semibold mb-4">Your Groups</h2>
            {loading ? (
              <div className="text-center py-8">Loading groups...</div>
            ) : groups.length === 0 ? (
              <div className="text-center py-8 text-gray-500">
                <p>You're not a member of any groups yet.</p>
                <p>Create a new group or join an existing one!</p>
              </div>
            ) : (
              <div className="groups-grid">
                {groups.map(group => (
                  <div key={group.id} className="group-card">
                    <div className="group-header">
                      <h3 className="group-name">{group.name}</h3>
                      <span className="group-role">
                        {group.user_role === 'admin' ? 'Group Admin' : group.user_role === 'member' ? 'Member' : group.user_role}
                      </span>
                    </div>
                    <p className="group-description">{group.description}</p>
                    <div className="group-meta">
                      <span className="group-members">{group.member_count} members</span>
                      <span className="group-creator">by {group.creator_name}</span>
                    </div>
                    <div className="group-actions">
                      <button 
                        onClick={() => openChat(group)}
                        className="btn btn-primary"
                      >
                        Open Chat
                      </button>
                      {group.user_role === 'admin' || userInfo?.IsAdmin ? (
                        <>
                          {group.user_role === 'admin' && (
                            <button 
                              onClick={() => startEditGroup(group)}
                              className="btn btn-secondary"
                            >
                              Edit
                            </button>
                          )}
                          <button 
                            onClick={() => {
                              if (window.confirm(`Are you sure you want to delete the group "${group.name}"? This action cannot be undone.`)) {
                                deleteGroup(group.id);
                              }
                            }}
                            className="btn btn-secondary text-red-600"
                          >
                            Delete
                          </button>
                        </>
                      ) : (
                        <button 
                          onClick={() => leaveGroup(group.id)}
                          className="btn btn-secondary"
                        >
                          Leave
                        </button>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {currentView === 'discover' && (
          <div className="discover-view">
            <h2 className="text-xl font-semibold mb-4">Discover Groups</h2>
            {loading ? (
              <div className="text-center py-8">Loading groups...</div>
            ) : discoverGroups.length === 0 ? (
              <div className="text-center py-8 text-gray-500">
                <p>No groups available to join.</p>
                <p>Create a new group to get started!</p>
              </div>
            ) : (
              <div className="groups-grid">
                {discoverGroups.map(group => (
                  <div key={group.id} className="group-card">
                    <div className="group-header">
                      <h3 className="group-name">{group.name}</h3>
                      <span className="group-role">
                        {group.user_role === 'admin' ? 'Group Admin' : group.user_role === 'member' ? 'Member' : group.user_role === 'not_member' ? 'Not A Member' : group.user_role || 'Available'}
                      </span>
                    </div>
                    <p className="group-description">{group.description}</p>
                    <div className="group-meta">
                      <span className="group-members">{group.member_count} members</span>
                      <span className="group-creator">by {group.creator_name}</span>
                    </div>
                    <div className="group-actions">
                      {group.user_role ? (
                        <>
                          <button 
                            onClick={() => openChat(group)}
                            className="btn btn-primary"
                          >
                            Open Chat
                          </button>
                          {(group.user_role === 'admin' || userInfo?.IsAdmin) && (
                            <>
                              {group.user_role === 'admin' && (
                                <button 
                                  onClick={() => startEditGroup(group)}
                                  className="btn btn-secondary"
                                >
                                  Edit
                                </button>
                              )}
                              <button 
                                onClick={() => {
                                  if (window.confirm(`Are you sure you want to delete the group "${group.name}"? This action cannot be undone.`)) {
                                    deleteGroup(group.id);
                                  }
                                }}
                                className="btn btn-secondary text-red-600"
                              >
                                Delete
                              </button>
                            </>
                          )}
                        </>
                      ) : (
                        <>
                          <button 
                            onClick={() => joinGroup(group.id)}
                            className="btn btn-primary"
                          >
                            Join Group
                          </button>
                          {userInfo?.IsAdmin && (
                            <button 
                              onClick={() => {
                                if (window.confirm(`Are you sure you want to delete the group "${group.name}"? This action cannot be undone.`)) {
                                  deleteGroup(group.id);
                                }
                              }}
                              className="btn btn-secondary text-red-600"
                            >
                              Delete (Admin)
                            </button>
                          )}
                        </>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {currentView === 'create-group' && (
          <div className="create-group-view">
            <h2 className="text-xl font-semibold mb-4">Create New Group</h2>
            <form onSubmit={createGroup} className="create-group-form" aria-label="Create new group form">
              <div className="form-group">
                <label htmlFor="groupName" className="form-label">Group Name</label>
                <input
                  type="text"
                  id="groupName"
                  value={groupName}
                  onChange={(e) => setGroupName(e.target.value)}
                  className="input"
                  placeholder="Enter group name"
                  required
                  aria-describedby={error ? "group-error" : undefined}
                  aria-invalid={error ? "true" : "false"}
                />
              </div>
              <div className="form-group">
                <label htmlFor="groupDescription" className="form-label">Description</label>
                <textarea
                  id="groupDescription"
                  value={groupDescription}
                  onChange={(e) => setGroupDescription(e.target.value)}
                  className="input"
                  rows="3"
                  placeholder="Describe your group (optional)"
                  aria-describedby="group-description-hint"
                />
                <span id="group-description-hint" className="sr-only">Optional description for your group</span>
              </div>
              <button 
                type="submit" 
                className="btn btn-primary"
                disabled={loading || !groupName.trim()}
                aria-busy={loading}
                aria-live="polite"
              >
                {loading ? 'Creating...' : 'Create Group'}
              </button>
            </form>
          </div>
        )}

        {currentView === 'edit-group' && editingGroup && (
          <div className="edit-group-view">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-xl font-semibold">Edit Group</h2>
              <button 
                onClick={cancelEditGroup}
                className="btn btn-secondary"
              >
                Cancel
              </button>
            </div>
            <form onSubmit={submitEditGroup} className="edit-group-form" aria-label="Edit group form">
              <div className="form-group">
                <label htmlFor="editGroupName" className="form-label">Group Name</label>
                <input
                  type="text"
                  id="editGroupName"
                  value={editGroupName}
                  onChange={(e) => setEditGroupName(e.target.value)}
                  className="input"
                  placeholder="Enter group name"
                  required
                  aria-describedby={error ? "edit-group-error" : undefined}
                  aria-invalid={error ? "true" : "false"}
                />
              </div>
              <div className="form-group">
                <label htmlFor="editGroupDescription" className="form-label">Description</label>
                <textarea
                  id="editGroupDescription"
                  value={editGroupDescription}
                  onChange={(e) => setEditGroupDescription(e.target.value)}
                  className="input"
                  rows="3"
                  placeholder="Describe your group (optional)"
                  aria-describedby="edit-group-description-hint"
                />
                <span id="edit-group-description-hint" className="sr-only">Optional description for your group</span>
              </div>
              <div className="flex gap-3">
                <button 
                  type="submit" 
                  className="btn btn-primary"
                  disabled={loading || !editGroupName.trim()}
                  aria-busy={loading}
                  aria-live="polite"
                >
                  {loading ? 'Updating...' : 'Update Group'}
                </button>
                <button 
                  type="button"
                  onClick={cancelEditGroup}
                  className="btn btn-secondary"
                  disabled={loading}
                >
                  Cancel
                </button>
              </div>
            </form>
          </div>
        )}

        {currentView === 'chat' && selectedGroup && (
          <div className="chat-view">
            <div className="chat-header-info">
              <button 
                onClick={() => setCurrentView('groups')}
                className="btn btn-ghost"
              >
                ← Back to Groups
              </button>
              <div className="chat-group-info">
                <h2 className="text-xl font-semibold">{selectedGroup.name}</h2>
                <p className="text-sm text-gray-600">{selectedGroup.member_count} members</p>
              </div>
            </div>

            <div className="messages-container" role="log" aria-live="polite" aria-label="Chat messages">
              {loading ? (
                <div className="text-center py-8" role="status" aria-live="polite">
                  <span className="sr-only">Loading messages</span>
                  Loading messages...
                </div>
              ) : messages.length === 0 ? (
                <div className="text-center py-8 text-gray-500" role="status">
                  <p>No messages yet. Start the conversation!</p>
                </div>
              ) : (
                <div className="messages-list" role="list">
                  {messages.map((message, index) => {
                    const showDate = index === 0 || 
                      formatDate(message.created_at) !== formatDate(messages[index - 1]?.created_at);
                    
                    return (
                      <div key={message.id} role="listitem">
                        {showDate && (
                          <div className="message-date" role="heading" aria-level="3">
                            {formatDate(message.created_at)}
                          </div>
                        )}
                        <div 
                          className={`message ${message.user_id === userInfo?.UserId ? 'own' : 'other'}`}
                          role="article"
                          aria-label={`Message from ${message.username} at ${formatTime(message.created_at)}`}
                        >
                          <div className="message-header">
                            <span className="message-username" aria-label="Message author">{message.username}</span>
                            <span className="message-time" aria-label="Message time">{formatTime(message.created_at)}</span>
                          </div>
                          <div className="message-content">
                            {message.content}
                            {message.is_edited && (
                              <span className="message-edited" aria-label="This message was edited">(edited)</span>
                            )}
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>

            <form onSubmit={sendMessage} className="message-form" aria-label="Send message form">
              <div className="message-input-container">
                <label htmlFor="newMessage" className="sr-only">Type your message</label>
                <input
                  type="text"
                  id="newMessage"
                  value={newMessage}
                  onChange={(e) => setNewMessage(e.target.value)}
                  className="message-input"
                  placeholder="Type your message..."
                  disabled={loading}
                  aria-describedby="message-hint"
                  aria-label="Message input"
                />
                <span id="message-hint" className="sr-only">Type your message and press Enter or click Send</span>
                <button 
                  type="submit" 
                  className="btn btn-primary"
                  disabled={loading || !newMessage.trim()}
                  aria-busy={loading}
                  aria-live="polite"
                  aria-label="Send message"
                >
                  Send
                </button>
              </div>
            </form>
          </div>
        )}
      </div>

    </div>
  );
}

export default ChatSystem;
