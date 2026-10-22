import React from "react";
import { Link, useNavigate, useParams, useLocation } from "react-router-dom";
import { Terminal, Code2, MessageSquare, FolderGit2, LogOut, User } from "lucide-react";
import { useAuth } from "../context/AuthContext";

export const Navbar: React.FC = () => {
  const { user, logout, isAuthenticated } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const { projectId } = useParams<{ projectId?: string }>();

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  return (
    <header className="border-b border-[#21262d] bg-[#161b22] px-6 py-3 select-none">
      <div className="flex items-center justify-between max-w-7xl mx-auto">
        {/* Brand */}
        <div className="flex items-center space-x-6">
          <Link to="/" className="flex items-center space-x-2.5 text-white font-semibold text-lg hover:text-brand-400 transition-colors">
            <div className="p-1.5 bg-brand-600/20 text-brand-400 rounded-md border border-brand-500/30">
              <Terminal className="w-5 h-5" />
            </div>
            <span>Codebase Intelligence</span>
          </Link>

          {/* Contextual Project Tabs */}
          {isAuthenticated && projectId && (
            <nav className="flex items-center space-x-1 pl-4 border-l border-[#30363d]">
              <Link
                to={`/projects/${projectId}/explorer`}
                className={`flex items-center space-x-1.5 px-3 py-1.5 text-sm rounded-md transition-colors ${
                  location.pathname.includes("/explorer")
                    ? "bg-[#21262d] text-white font-medium"
                    : "text-[#8b949e] hover:text-[#c9d1d9] hover:bg-[#21262d]/50"
                }`}
              >
                <Code2 className="w-4 h-4" />
                <span>Source Explorer</span>
              </Link>
              <Link
                to={`/projects/${projectId}/chat`}
                className={`flex items-center space-x-1.5 px-3 py-1.5 text-sm rounded-md transition-colors ${
                  location.pathname.includes("/chat")
                    ? "bg-[#21262d] text-white font-medium"
                    : "text-[#8b949e] hover:text-[#c9d1d9] hover:bg-[#21262d]/50"
                }`}
              >
                <MessageSquare className="w-4 h-4" />
                <span>AI Architecture Chat</span>
              </Link>
            </nav>
          )}
        </div>

        {/* Right Nav */}
        <div className="flex items-center space-x-4">
          {isAuthenticated ? (
            <>
              <Link
                to="/"
                className="flex items-center space-x-1.5 text-sm text-[#8b949e] hover:text-white transition-colors px-2 py-1"
              >
                <FolderGit2 className="w-4 h-4" />
                <span>Projects</span>
              </Link>

              <div className="flex items-center space-x-2 pl-4 border-l border-[#30363d]">
                <div className="flex items-center space-x-2 px-2.5 py-1 rounded bg-[#21262d] text-xs text-[#c9d1d9]">
                  <User className="w-3.5 h-3.5 text-brand-400" />
                  <span className="max-w-[150px] truncate">{user?.email}</span>
                </div>
                <button
                  onClick={handleLogout}
                  title="Sign out"
                  className="p-1.5 text-[#8b949e] hover:text-rose-400 hover:bg-[#21262d] rounded transition-colors"
                >
                  <LogOut className="w-4 h-4" />
                </button>
              </div>
            </>
          ) : (
            <div className="flex items-center space-x-3 text-sm">
              <Link to="/login" className="text-[#8b949e] hover:text-white transition-colors">
                Sign In
              </Link>
              <Link
                to="/register"
                className="px-3 py-1.5 bg-brand-600 hover:bg-brand-500 text-white rounded-md font-medium text-xs transition-colors"
              >
                Get Started
              </Link>
            </div>
          )}
        </div>
      </div>
    </header>
  );
};
