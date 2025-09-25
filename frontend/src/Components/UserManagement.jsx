import { useState, useEffect } from "react";
import axios from "axios";

function UserManagement({ onSignOut }) {
  const [users, setUsers] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    fetchUsers();
  }, []);

  const fetchUsers = async () => {
    try {
      setIsLoading(true);
      const response = await axios.get("http://localhost:5002/users");
      if (response.data.users) {
        setUsers(response.data.users);
      }
    } catch (err) {
      setError("Failed to fetch users. Please try again.");
      console.error("Fetch users error:", err);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="w-full h-full bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-100 flex items-center justify-center px-4">
      <div className="w-full max-w-6xl">
        {/* Header */}
        <div className="text-center mb-16" style={{marginBottom: '4rem'}}>
          <h1 className="text-5xl font-bold text-slate-900 mb-6 tracking-tight" style={{fontSize: '3rem', fontWeight: 'bold', color: '#0f172a', marginBottom: '1.5rem'}}>👥 User Management</h1>
          <p className="text-slate-600 text-xl font-medium mb-2" style={{color: '#475569', fontSize: '1.25rem', fontWeight: '500', marginBottom: '0.5rem'}}>Manage registered users and their information</p>
          <p className="text-slate-500 text-base" style={{color: '#64748b', fontSize: '1rem'}}>View and manage all users in the system</p>
        </div>

        {/* Main Content */}
        <div className="bg-white/95 backdrop-blur-sm rounded-3xl shadow-2xl p-12 border border-white/30" style={{backgroundColor: 'rgba(255, 255, 255, 0.95)', borderRadius: '1.5rem', padding: '3rem', boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.25)'}}>
          <div className="text-center mb-8">
            <h2 className="text-3xl font-bold text-slate-900 mb-2" style={{fontSize: '1.875rem', fontWeight: 'bold', color: '#0f172a'}}>👥 Registered Users</h2>
            <p className="text-slate-600" style={{color: '#475569'}}>Manage and view all registered users in the system</p>
          </div>

          {/* Action Buttons */}
          <div className="flex flex-col sm:flex-row gap-4 mb-8" style={{display: 'flex', flexDirection: 'row', gap: '1rem', marginBottom: '2rem'}}>
            <button
              onClick={fetchUsers}
              className="flex-1 py-4 px-6 bg-gradient-to-r from-blue-600 via-blue-700 to-indigo-700 text-white rounded-xl hover:from-blue-700 hover:via-blue-800 hover:to-indigo-800 focus:ring-4 focus:ring-blue-500/30 focus:ring-offset-2 transition-all duration-300 font-semibold shadow-lg hover:shadow-xl transform hover:scale-[1.02] active:scale-[0.98]"
              style={{padding: '1rem 1.5rem', borderRadius: '0.75rem', fontWeight: '600'}}
              disabled={isLoading}
            >
              {isLoading ? "Refreshing..." : "🔄 Refresh Users"}
            </button>
            <button
              onClick={onSignOut}
              className="flex-1 py-4 px-6 bg-gradient-to-r from-red-500 via-red-600 to-red-700 text-white rounded-xl hover:from-red-600 hover:via-red-700 hover:to-red-800 focus:ring-4 focus:ring-red-500/30 focus:ring-offset-2 transition-all duration-300 font-semibold shadow-lg hover:shadow-xl transform hover:scale-[1.02] active:scale-[0.98]"
              style={{padding: '1rem 1.5rem', borderRadius: '0.75rem', fontWeight: '600'}}
            >
              🚪 Sign Out
            </button>
          </div>

          {/* User Count */}
          <div className="bg-gradient-to-r from-blue-50 to-indigo-50 rounded-2xl p-6 border border-blue-200 mb-8" style={{backgroundColor: 'rgba(239, 246, 255, 0.5)', borderRadius: '1rem', padding: '1.5rem', marginBottom: '2rem'}}>
            <div className="text-center">
              <div className="text-3xl font-bold text-blue-600 mb-2" style={{fontSize: '1.875rem', fontWeight: 'bold', color: '#2563eb'}}>{users.length}</div>
              <div className="text-lg text-slate-600" style={{fontSize: '1.125rem', color: '#475569'}}>Total Users</div>
            </div>
          </div>

          {error && (
            <div className="mb-6 bg-red-50/80 border-2 border-red-200 rounded-xl p-4">
              <p className="text-sm font-semibold text-red-800">{error}</p>
            </div>
          )}

          {isLoading ? (
            <div className="text-center py-12">
              <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
              <p className="mt-4 text-slate-600">Loading users...</p>
            </div>
          ) : users.length === 0 ? (
            <div className="text-center py-12">
              <div className="text-6xl mb-4">👥</div>
              <h3 className="text-xl font-bold text-slate-900 mb-2">No users found</h3>
              <p className="text-slate-600">No users have registered yet.</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
              {users.map((user) => (
                <div key={user.UserId} className="group bg-white/95 backdrop-blur-sm rounded-3xl shadow-xl p-8 border border-white/30 hover:shadow-2xl transition-all duration-500 transform hover:scale-[1.02] hover:-translate-y-2" style={{backgroundColor: 'rgba(255, 255, 255, 0.95)', borderRadius: '1.5rem', padding: '2rem', boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.1)'}}>
                  <div className="space-y-6">
                    {/* Enhanced User Avatar */}
                    <div className="flex items-center space-x-4">
                      <div className="w-16 h-16 bg-gradient-to-br from-blue-500 via-purple-600 to-indigo-700 rounded-full flex items-center justify-center text-white font-bold text-xl shadow-lg" style={{width: '4rem', height: '4rem', fontSize: '1.25rem'}}>
                        {user.UserName.charAt(0).toUpperCase()}
                      </div>
                      <div>
                        <h4 className="text-xl font-bold text-slate-900 group-hover:text-blue-600 transition-colors duration-300" style={{fontSize: '1.25rem', fontWeight: 'bold'}}>
                          {user.UserName}
                        </h4>
                        <p className="text-sm text-slate-600 font-medium" style={{fontSize: '0.875rem', fontWeight: '500'}}>User ID: {user.UserId}</p>
                      </div>
                    </div>
                    
                    {/* User Email */}
                    <div className="space-y-2">
                      <p className="text-sm text-slate-500">Email Address</p>
                      <p className="text-sm text-slate-700 bg-slate-50 rounded-lg p-3 font-mono">
                        {user.UserEmail}
                      </p>
                    </div>
                    
                    {/* Registration Date */}
                    <div className="space-y-2">
                      <p className="text-sm text-slate-500">Registered</p>
                      <p className="text-sm text-slate-700">
                        {new Date(user.CreatedAt).toLocaleDateString('en-US', {
                          year: 'numeric',
                          month: 'long',
                          day: 'numeric',
                          hour: '2-digit',
                          minute: '2-digit'
                        })}
                      </p>
                    </div>
                    
                    {/* User Status */}
                    <div className="flex items-center justify-between pt-4 border-t border-slate-200">
                      <span className="px-3 py-1 bg-green-100 text-green-800 text-xs rounded-full font-semibold">
                        Active
                      </span>
                      <span className="text-xs text-slate-500">
                        Member since {new Date(user.CreatedAt).getFullYear()}
                      </span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default UserManagement;
