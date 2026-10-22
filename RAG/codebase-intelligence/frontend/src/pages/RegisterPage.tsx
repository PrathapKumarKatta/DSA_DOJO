import React, { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Terminal, Lock, Mail, AlertCircle, Loader2 } from "lucide-react";
import { api } from "../services/api";
import { useAuth } from "../context/AuthContext";

export const RegisterPage: React.FC = () => {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (password !== confirmPassword) {
      setError("Passwords do not match.");
      return;
    }

    if (password.length < 8) {
      setError("Password must be at least 8 characters long.");
      return;
    }

    setIsLoading(true);

    try {
      await api.register(email, password);
      // Automatically log in after registration
      const tokens = await api.login(email, password);
      const user = await api.getMe();
      login(tokens.access_token, user);
      navigate("/");
    } catch (err: any) {
      setError(err.message || "Failed to register account.");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#0d1117] flex flex-col justify-center py-12 sm:px-6 lg:px-8">
      <div className="sm:mx-auto sm:w-full sm:max-w-md text-center">
        <div className="inline-flex p-3 bg-brand-600/15 border border-brand-500/30 rounded-xl text-brand-400 mb-4">
          <Terminal className="w-8 h-8" />
        </div>
        <h2 className="text-2xl font-bold text-white tracking-tight">Create your developer account</h2>
        <p className="mt-2 text-sm text-[#8b949e]">
          Already have an account?{" "}
          <Link to="/login" className="text-brand-400 hover:text-brand-300 font-medium">
            Sign in
          </Link>
        </p>
      </div>

      <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-md">
        <div className="bg-[#161b22] py-8 px-6 border border-[#30363d] shadow-xl sm:rounded-xl sm:px-10">
          <form onSubmit={handleSubmit} className="space-y-4">
            {error && (
              <div className="p-3 bg-rose-500/10 border border-rose-500/30 rounded-lg text-rose-400 text-xs flex items-center space-x-2">
                <AlertCircle className="w-4 h-4 shrink-0" />
                <span>{error}</span>
              </div>
            )}

            <div>
              <label className="block text-xs font-medium text-[#8b949e] mb-1.5">Email address</label>
              <div className="relative">
                <Mail className="w-4 h-4 text-[#8b949e] absolute left-3 top-1/2 -translate-y-1/2" />
                <input
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="developer@company.com"
                  className="w-full bg-[#0d1117] border border-[#30363d] rounded-lg pl-9 pr-3.5 py-2 text-sm text-white placeholder-[#484f58] focus:outline-none focus:border-brand-500"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-medium text-[#8b949e] mb-1.5">Password</label>
              <div className="relative">
                <Lock className="w-4 h-4 text-[#8b949e] absolute left-3 top-1/2 -translate-y-1/2" />
                <input
                  type="password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="At least 8 characters"
                  className="w-full bg-[#0d1117] border border-[#30363d] rounded-lg pl-9 pr-3.5 py-2 text-sm text-white placeholder-[#484f58] focus:outline-none focus:border-brand-500"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-medium text-[#8b949e] mb-1.5">Confirm Password</label>
              <div className="relative">
                <Lock className="w-4 h-4 text-[#8b949e] absolute left-3 top-1/2 -translate-y-1/2" />
                <input
                  type="password"
                  required
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  placeholder="Repeat your password"
                  className="w-full bg-[#0d1117] border border-[#30363d] rounded-lg pl-9 pr-3.5 py-2 text-sm text-white placeholder-[#484f58] focus:outline-none focus:border-brand-500"
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={isLoading}
              className="w-full mt-2 py-2.5 bg-brand-600 hover:bg-brand-500 text-white rounded-lg text-sm font-medium transition-colors flex items-center justify-center space-x-2 disabled:opacity-50"
            >
              {isLoading && <Loader2 className="w-4 h-4 animate-spin" />}
              <span>{isLoading ? "Creating account..." : "Create Account"}</span>
            </button>
          </form>
        </div>
      </div>
    </div>
  );
};
