import { useState, useEffect } from "react";
import axios from "axios";
import { API_BASE_URL } from "../config";
import { csrfManager } from "../utils/security";
import { tokenStorage } from "../utils/tokenStorage";

// Avatar Component
function Avatar({ name, size = 48 }) {
  const getInitials = (name) => {
    if (!name) return "?";
    const parts = name.trim().split(" ");
    if (parts.length >= 2) {
      return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
    }
    return name.substring(0, 2).toUpperCase();
  };

  const getColorFromName = (name) => {
    if (!name) return "#2563EB";
    const colors = [
      { bg: "#2563EB", text: "white" }, // blue
      { bg: "#9333EA", text: "white" }, // purple
      { bg: "#10B981", text: "white" }, // green
      { bg: "#F59E0B", text: "white" }, // orange
      { bg: "#EF4444", text: "white" }, // red
    ];
    let hash = 0;
    for (let i = 0; i < name.length; i++) {
      hash = name.charCodeAt(i) + ((hash << 5) - hash);
    }
    return colors[Math.abs(hash) % colors.length];
  };

  const color = getColorFromName(name);
  const initials = getInitials(name);

  return (
    <div
      className="rounded-full flex items-center justify-center font-semibold"
      style={{
        width: `${size}px`,
        height: `${size}px`,
        backgroundColor: color.bg,
        color: color.text,
        fontSize: `${size * 0.375}px`,
      }}
    >
      {initials}
    </div>
  );
}

// Badge Component
function Badge({ type, label }) {
  const styles = {
    admin: { bg: "#2563EB", text: "white" },
    user: { bg: "#F3F4F6", text: "#6B7280" },
    active: { bg: "#D1FAE5", text: "#10B981" },
    pending: { bg: "#FEF3C7", text: "#F59E0B" },
    banned: { bg: "#FEE2E2", text: "#EF4444" },
  };

  const style = styles[type] || styles.user;

  return (
    <span
      className="inline-block font-medium"
      style={{
        padding: "4px 10px",
        borderRadius: "20px",
        fontSize: "12px",
        backgroundColor: style.bg,
        color: style.text,
      }}
    >
      {label}
    </span>
  );
}

// User Table Row Component
function UserTableRow({ user, onEdit, onDelete }) {
  return (
    <tr className="hover:bg-gray-50 transition-colors" style={{ height: "68px" }}>
      <td className="px-6 py-4 text-center">
        <div className="flex justify-center">
          <Avatar name={user.UserName} size={48} />
        </div>
      </td>
      <td className="px-6 py-4 text-center">
        <div className="text-sm font-bold text-gray-900">{user.UserName || "N/A"}</div>
      </td>
      <td className="px-6 py-4 text-center">
        <div className="text-sm text-gray-900">{user.UserEmail || "N/A"}</div>
      </td>
      <td className="px-6 py-4 text-center">
        <div className="flex justify-center">
          {user.IsAdmin ? (
            <Badge type="admin" label="Admin" />
          ) : (
            <Badge type="user" label="User" />
          )}
        </div>
      </td>
      <td className="px-6 py-4 text-center">
        <div className="flex justify-center">
          <Badge type="active" label="Active" />
        </div>
      </td>
      <td className="px-6 py-4 text-sm font-medium text-center">
        <div className="flex justify-center gap-2">
          <button
            onClick={() => onEdit(user)}
            className="px-3 py-1.5 rounded-lg font-medium transition-colors"
            style={{
              border: "1px solid #2563EB",
              background: "white",
              color: "#2563EB",
            }}
            onMouseEnter={(e) => (e.target.style.background = "#EFF6FF")}
            onMouseLeave={(e) => (e.target.style.background = "white")}
          >
            Edit
          </button>
          <button
            onClick={() => onDelete(user)}
            className="px-3 py-1.5 rounded-lg font-medium transition-colors"
            style={{
              background: "none",
              color: "#DC2626",
            }}
            onMouseEnter={(e) => (e.target.style.background = "#FEE2E2")}
            onMouseLeave={(e) => (e.target.style.background = "none")}
          >
            Delete
          </button>
        </div>
      </td>
    </tr>
  );
}

// User Card Component
function UserCard({ user, onEdit, onDelete }) {
  return (
    <div
      className="bg-white rounded-xl p-5 transition-shadow hover:shadow-md"
      style={{
        border: "1px solid #E5E7EB",
        boxShadow: "0 1px 2px rgba(0,0,0,0.08)",
      }}
    >
      <div className="flex items-start gap-4">
        <Avatar name={user.UserName} size={48} />
        <div className="flex-1">
          <div className="flex items-center justify-between mb-2">
            <h3 className="text-sm font-bold text-gray-900">{user.UserName || "N/A"}</h3>
            <div className="flex gap-2">
              {user.IsAdmin ? (
                <Badge type="admin" label="Admin" />
              ) : (
                <Badge type="user" label="User" />
              )}
              <Badge type="active" label="Active" />
            </div>
          </div>
          <p className="text-sm text-gray-600 mb-3">{user.UserEmail || "N/A"}</p>
          <div className="flex gap-2">
            <button
              onClick={() => onEdit(user)}
              className="px-3 py-1.5 rounded-lg text-sm font-medium transition-colors"
              style={{
                border: "1px solid #2563EB",
                background: "white",
                color: "#2563EB",
              }}
              onMouseEnter={(e) => (e.target.style.background = "#EFF6FF")}
              onMouseLeave={(e) => (e.target.style.background = "white")}
            >
              Edit
            </button>
            <button
              onClick={() => onDelete(user)}
              className="px-3 py-1.5 rounded-lg text-sm font-medium transition-colors"
              style={{
                background: "none",
                color: "#DC2626",
              }}
              onMouseEnter={(e) => (e.target.style.background = "#FEE2E2")}
              onMouseLeave={(e) => (e.target.style.background = "none")}
            >
              Delete
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

// Modal Component
function Modal({ isOpen, onClose, title, children }) {
  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 flex items-center justify-center z-[9999] p-4 overflow-y-auto"
      style={{ 
        backgroundColor: "rgba(0, 0, 0, 0.5)",
        position: "fixed",
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
      }}
      onClick={onClose}
    >
      <div
        className="rounded-xl shadow-lg my-auto"
        style={{
          backgroundColor: "#ffffff",
          padding: "20px 24px",
          boxShadow: "0 4px 10px rgba(0,0,0,0.15)",
          position: "relative",
          zIndex: 10000,
          opacity: 1,
          width: "90%",
          maxWidth: "420px",
        }}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-xl font-bold text-gray-900">{title}</h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 text-2xl leading-none"
            style={{ fontSize: "28px", lineHeight: "1" }}
          >
            ×
          </button>
        </div>
        {children}
      </div>
    </div>
  );
}

function UserManagement({ onSignOut, onBackToSearch }) {
  const [users, setUsers] = useState([]);
  const [filteredUsers, setFilteredUsers] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [viewMode, setViewMode] = useState("table"); // "table" or "card"
  
  // Search and filter states
  const [searchQuery, setSearchQuery] = useState("");
  const [filterRole, setFilterRole] = useState("all");
  
  // Modal states
  const [showAddModal, setShowAddModal] = useState(false);
  const [showEditModal, setShowEditModal] = useState(false);
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [selectedUser, setSelectedUser] = useState(null);
  
  // Form states
  const [formData, setFormData] = useState({
    username: "",
    email: "",
    password: "",
    isAdmin: false
  });
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => { 
    fetchUsers(); 
  }, []);

  useEffect(() => {
    filterUsers();
  }, [users, searchQuery, filterRole]);

  // Responsive: switch to card view on mobile
  useEffect(() => {
    const handleResize = () => {
      if (window.innerWidth < 768) {
        setViewMode("card");
      }
    };
    handleResize();
    window.addEventListener("resize", handleResize);
    return () => window.removeEventListener("resize", handleResize);
  }, []);

  // Prevent body scroll when modal is open
  useEffect(() => {
    if (showAddModal || showEditModal || showDeleteModal) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = 'unset';
    }
    return () => {
      document.body.style.overflow = 'unset';
    };
  }, [showAddModal, showEditModal, showDeleteModal]);

  const fetchUsers = async () => {
    try {
      setIsLoading(true);
      setError("");
      const { data } = await axios.get(`${API_BASE_URL}/users`);
      if (data?.users) {
        setUsers(data.users);
      }
    } catch (err) {
      console.error("Fetch users error:", err);
      setError("Unable to load users. Please try again later.");
    } finally {
      setIsLoading(false);
    }
  };

  const filterUsers = () => {
    let filtered = [...users];

    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase();
      filtered = filtered.filter(user => 
        user.UserName?.toLowerCase().includes(query) ||
        user.UserEmail?.toLowerCase().includes(query)
      );
    }

    if (filterRole !== "all") {
      filtered = filtered.filter(user => 
        filterRole === "admin" ? user.IsAdmin : !user.IsAdmin
      );
    }

    setFilteredUsers(filtered);
  };

  const handleAddUser = () => {
    setFormData({ username: "", email: "", password: "", isAdmin: false });
    setSelectedUser(null);
    setShowAddModal(true);
  };

  const handleEditUser = (user) => {
    setSelectedUser(user);
    setFormData({
      username: user.UserName || "",
      email: user.UserEmail || "",
      password: "",
      isAdmin: user.IsAdmin || false
    });
    setShowEditModal(true);
  };

  const handleDeleteUser = (user) => {
    setSelectedUser(user);
    setShowDeleteModal(true);
  };

  const handleSubmitAdd = async (e) => {
    e.preventDefault();
    setIsSubmitting(true);
    setError("");

    try {
      const token = tokenStorage.get();
      if (!token) {
        setError("Authentication required. Please sign in to continue.");
        setIsSubmitting(false);
        return;
      }

      const csrfToken = await csrfManager.getToken();
      const headers = {
        ...csrfManager.getHeaders(),
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      };

      const response = await axios.post(`${API_BASE_URL}/admin/users`, {
        username: formData.username,
        email: formData.email,
        password: formData.password,
        is_admin: formData.isAdmin || false
      }, { headers });

      setSuccess(`User "${formData.username}" added successfully!`);
      setShowAddModal(false);
      setFormData({ username: "", email: "", password: "", isAdmin: false });
      await fetchUsers();
      setTimeout(() => setSuccess(""), 3000);
    } catch (err) {
      setError(err.response?.data?.error || "Unable to create user. Please verify the information and try again.");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleSubmitEdit = async (e) => {
    e.preventDefault();
    if (!selectedUser) return;
    
    setIsSubmitting(true);
    setError("");

    try {
      const token = tokenStorage.get();
      if (!token) {
        setError("Authentication required. Please sign in to continue.");
        setIsSubmitting(false);
        return;
      }

      const csrfToken = await csrfManager.getToken();
      const headers = {
        ...csrfManager.getHeaders(),
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      };

      const payload = {
        username: formData.username,
        email: formData.email,
        is_admin: formData.isAdmin || false
      };
      if (formData.password) {
        payload.password = formData.password;
      }

      const response = await axios.put(`${API_BASE_URL}/admin/users/${selectedUser.UserId}`, payload, { headers });

      setSuccess(`User "${formData.username}" updated successfully!`);
      setShowEditModal(false);
      setFormData({ username: "", email: "", password: "", isAdmin: false });
      setSelectedUser(null);
      await fetchUsers();
      setTimeout(() => setSuccess(""), 3000);
    } catch (err) {
      setError(err.response?.data?.error || "Unable to update user. Please verify the information and try again.");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleConfirmDelete = async () => {
    if (!selectedUser) return;
    
    setIsSubmitting(true);
    setError("");

    try {
      const token = tokenStorage.get();
      if (!token) {
        setError("Authentication required. Please sign in to continue.");
        setIsSubmitting(false);
        return;
      }

      const csrfToken = await csrfManager.getToken();
      const headers = {
        ...csrfManager.getHeaders(),
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      };

      await axios.delete(`${API_BASE_URL}/admin/users/${selectedUser.UserId}`, { headers });

      setSuccess(`User "${selectedUser.UserName}" deleted successfully!`);
      setShowDeleteModal(false);
      setSelectedUser(null);
      await fetchUsers();
      setTimeout(() => setSuccess(""), 3000);
    } catch (err) {
      setError(err.response?.data?.error || "Unable to delete user. Please try again.");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header Bar */}
      <div className="bg-white border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            {onBackToSearch && (
              <button 
                onClick={onBackToSearch}
                className="btn btn-secondary"
              >
                ← Back
              </button>
            )}
            <div className="flex-1"></div>
            <button 
              onClick={onSignOut} 
              className="btn btn-secondary"
            >
              Sign Out
            </button>
          </div>
        </div>
      </div>

      {/* Main Container */}
      <div className="max-w-5xl mx-auto px-6 py-8" style={{ maxWidth: "1000px", padding: "32px" }}>
        {/* Page Header */}
        <div className="mb-6 flex items-center justify-between">
          <h1 className="text-3xl font-bold text-gray-900">Manage Users</h1>
          <button
            onClick={handleAddUser}
            className="btn btn-primary"
          >
            + Add User
          </button>
        </div>

        {/* Search and Filter Bar */}
        <div className="mb-6 flex gap-4 flex-col sm:flex-row">
          <div className="flex-1 relative">
            <input
              type="text"
              placeholder="Search users..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full px-4 py-2.5 pl-10 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm"
              style={{
                backgroundColor: "white",
                border: "1px solid #E5E7EB",
                borderRadius: "8px",
                color: "#111827",
              }}
              onFocus={(e) => (e.target.style.borderColor = "#2563EB")}
              onBlur={(e) => (e.target.style.borderColor = "#E5E7EB")}
            />
            <div className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400">
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
              </svg>
            </div>
          </div>
          
          <select
            value={filterRole}
            onChange={(e) => setFilterRole(e.target.value)}
            className="px-4 py-2.5 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm sm:w-auto w-full"
            style={{
              backgroundColor: "white",
              border: "1px solid #E5E7EB",
              borderRadius: "8px",
              color: "#111827",
            }}
            onFocus={(e) => (e.target.style.borderColor = "#2563EB")}
            onBlur={(e) => (e.target.style.borderColor = "#E5E7EB")}
          >
            <option value="all">All Roles</option>
            <option value="admin">Admin</option>
            <option value="user">User</option>
          </select>
        </div>

        {/* Success/Error Messages */}
        {success && (
          <div className="mb-4 bg-green-50 border border-green-200 text-green-800 px-4 py-3 rounded-lg">
            {success}
          </div>
        )}
        {error && (
          <div className="mb-4 bg-red-50 border border-red-200 text-red-800 px-4 py-3 rounded-lg">
            {error}
          </div>
        )}

        {/* Users Table/Card View */}
        {isLoading ? (
          <div className="bg-white rounded-xl p-12 text-center" style={{ boxShadow: "0 1px 3px rgba(0,0,0,0.08)" }}>
            <div className="inline-block w-8 h-8 border-4 border-blue-200 border-t-blue-600 rounded-full animate-spin"></div>
            <p className="mt-4 text-gray-600">Loading users...</p>
          </div>
        ) : filteredUsers.length === 0 ? (
          <div className="bg-white rounded-xl p-12 text-center" style={{ boxShadow: "0 1px 3px rgba(0,0,0,0.08)" }}>
            <p className="text-gray-600">
              {searchQuery || filterRole !== "all" 
                ? "No users match your search criteria" 
                : "No users found"}
            </p>
          </div>
        ) : viewMode === "card" || window.innerWidth < 768 ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
            {filteredUsers.map((user) => (
              <UserCard
                key={user.UserId}
                user={user}
                onEdit={handleEditUser}
                onDelete={handleDeleteUser}
              />
            ))}
          </div>
        ) : (
          <div
            className="bg-white rounded-xl overflow-hidden"
            style={{
              borderRadius: "12px",
              boxShadow: "0 1px 3px rgba(0,0,0,0.08)",
            }}
          >
            <table className="w-full">
              <thead className="bg-gray-50 border-b border-gray-200">
                <tr>
                  <th className="px-6 py-3 text-center text-xs font-semibold text-gray-700 uppercase tracking-wider">Avatar</th>
                  <th className="px-6 py-3 text-center text-xs font-semibold text-gray-700 uppercase tracking-wider">Name</th>
                  <th className="px-6 py-3 text-center text-xs font-semibold text-gray-700 uppercase tracking-wider">Email</th>
                  <th className="px-6 py-3 text-center text-xs font-semibold text-gray-700 uppercase tracking-wider">Role</th>
                  <th className="px-6 py-3 text-center text-xs font-semibold text-gray-700 uppercase tracking-wider">Status</th>
                  <th className="px-6 py-3 text-center text-xs font-semibold text-gray-700 uppercase tracking-wider">Actions</th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {filteredUsers.map((user) => (
                  <UserTableRow
                    key={user.UserId}
                    user={user}
                    onEdit={handleEditUser}
                    onDelete={handleDeleteUser}
                  />
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Add User Modal */}
      <Modal isOpen={showAddModal} onClose={() => setShowAddModal(false)} title="Add New User">
        <form onSubmit={handleSubmitAdd} className="space-y-5">
          <div>
            <label htmlFor="add-username" className="block text-sm font-bold text-slate-700 mb-2">Username</label>
            <input
              id="add-username"
              type="text"
              required
              value={formData.username}
              onChange={(e) => setFormData({...formData, username: e.target.value})}
              className="input"
              placeholder="Your display name"
              style={{ width: "100%", boxSizing: "border-box" }}
            />
          </div>
          <div>
            <label htmlFor="add-email" className="block text-sm font-bold text-slate-700 mb-2">Email</label>
            <input
              id="add-email"
              type="email"
              required
              value={formData.email}
              onChange={(e) => setFormData({...formData, email: e.target.value})}
              className="input"
              placeholder="you@example.com"
              style={{ width: "100%", boxSizing: "border-box" }}
            />
          </div>
          <div>
            <label htmlFor="add-password" className="block text-sm font-bold text-slate-700 mb-2">Password</label>
            <input
              id="add-password"
              type="password"
              required
              value={formData.password}
              onChange={(e) => setFormData({...formData, password: e.target.value})}
              className="input"
              placeholder="At least 6 characters"
              style={{ width: "100%", boxSizing: "border-box" }}
            />
          </div>
          <div className="flex items-center">
            <input
              type="checkbox"
              id="isAdmin"
              checked={formData.isAdmin}
              onChange={(e) => setFormData({...formData, isAdmin: e.target.checked})}
              className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
            />
            <label htmlFor="isAdmin" className="ml-2 text-sm font-bold text-slate-700">Admin privileges</label>
          </div>
          {error && (
            <div 
              className="glass p-3 rounded-lg border border-red-200/70 text-red-700 text-sm"
              role="alert"
              aria-live="polite"
              aria-atomic="true"
            >
              {error}
            </div>
          )}
          <div className="flex gap-3">
            <button
              type="button"
              onClick={() => setShowAddModal(false)}
              className="btn btn-secondary flex-1"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className="btn btn-primary flex-1"
              aria-busy={isSubmitting}
            >
              {isSubmitting ? "Adding…" : "Add User"}
            </button>
          </div>
        </form>
      </Modal>

      {/* Edit User Modal */}
      <Modal isOpen={showEditModal} onClose={() => setShowEditModal(false)} title="Edit User">
        <form onSubmit={handleSubmitEdit} className="space-y-5">
          <div>
            <label htmlFor="edit-username" className="block text-sm font-bold text-slate-700 mb-2">Username</label>
            <input
              id="edit-username"
              type="text"
              required
              value={formData.username}
              onChange={(e) => setFormData({...formData, username: e.target.value})}
              className="input"
              placeholder="Your display name"
              style={{ width: "100%", boxSizing: "border-box" }}
            />
          </div>
          <div>
            <label htmlFor="edit-email" className="block text-sm font-bold text-slate-700 mb-2">Email</label>
            <input
              id="edit-email"
              type="email"
              required
              value={formData.email}
              onChange={(e) => setFormData({...formData, email: e.target.value})}
              className="input"
              placeholder="you@example.com"
              style={{ width: "100%", boxSizing: "border-box" }}
            />
          </div>
          <div>
            <label htmlFor="edit-password" className="block text-sm font-bold text-slate-700 mb-2">New Password (leave blank to keep current)</label>
            <input
              id="edit-password"
              type="password"
              value={formData.password}
              onChange={(e) => setFormData({...formData, password: e.target.value})}
              className="input"
              placeholder="Leave blank to keep current password"
              style={{ width: "100%", boxSizing: "border-box" }}
            />
          </div>
          <div className="flex items-center">
            <input
              type="checkbox"
              id="editIsAdmin"
              checked={formData.isAdmin}
              onChange={(e) => setFormData({...formData, isAdmin: e.target.checked})}
              className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
            />
            <label htmlFor="editIsAdmin" className="ml-2 text-sm font-bold text-slate-700">Admin privileges</label>
          </div>
          {error && (
            <div 
              className="glass p-3 rounded-lg border border-red-200/70 text-red-700 text-sm"
              role="alert"
              aria-live="polite"
              aria-atomic="true"
            >
              {error}
            </div>
          )}
          <div className="flex gap-3">
            <button
              type="button"
              onClick={() => setShowEditModal(false)}
              className="btn btn-secondary flex-1"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className="btn btn-primary flex-1"
              aria-busy={isSubmitting}
            >
              {isSubmitting ? "Updating…" : "Update User"}
            </button>
          </div>
        </form>
      </Modal>

      {/* Delete Confirmation Modal */}
      <Modal isOpen={showDeleteModal} onClose={() => setShowDeleteModal(false)} title="Delete User">
        <p className="text-gray-700 mb-6">
          Are you sure you want to delete user <strong>"{selectedUser?.UserName}"</strong>? 
          This action cannot be undone.
        </p>
        <div className="flex gap-3">
          <button
            type="button"
            onClick={() => setShowDeleteModal(false)}
            className="flex-1 px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition-colors font-medium border border-gray-300"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={handleConfirmDelete}
            disabled={isSubmitting}
            className="flex-1 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 disabled:opacity-50 transition-colors font-medium"
          >
            {isSubmitting ? "Deleting..." : "Delete User"}
          </button>
        </div>
      </Modal>
    </div>
  );
}

export default UserManagement;
