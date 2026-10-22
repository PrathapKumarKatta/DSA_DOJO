import React, { useState } from "react";
import { Upload, X, AlertCircle, CheckCircle2, Loader2, FileCode } from "lucide-react";
import { api } from "../services/api";

interface ProjectUploadModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

export const ProjectUploadModal: React.FC<ProjectUploadModalProps> = ({
  isOpen,
  onClose,
  onSuccess,
}) => {
  const [name, setName] = useState("");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      if (!file.name.toLowerCase().endsWith(".zip")) {
        setError("Please select a valid .zip archive.");
        setSelectedFile(null);
        return;
      }
      setSelectedFile(file);
      setError(null);
      if (!name) {
        setName(file.name.replace(/\.zip$/i, ""));
      }
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) {
      setError("Please specify a project name.");
      return;
    }
    if (!selectedFile) {
      setError("Please select a .zip archive to upload.");
      return;
    }

    try {
      setIsUploading(true);
      setError(null);
      setStatusMessage("Creating project record...");

      // 1. Create project
      const project = await api.createProject(name.trim());

      // 2. Upload ZIP
      setStatusMessage("Uploading repository archive...");
      await api.uploadCodebase(project.id, selectedFile);

      // 3. Poll indexing status
      setStatusMessage("Parsing AST symbols and indexing code...");
      let attempts = 0;
      const interval = setInterval(async () => {
        attempts++;
        try {
          const statusRes = await api.getProjectStatus(project.id);
          if (statusRes.project_status === "ready") {
            clearInterval(interval);
            setStatusMessage("Indexing completed successfully!");
            setTimeout(() => {
              setIsUploading(false);
              onSuccess();
              onClose();
            }, 800);
          } else if (statusRes.project_status === "failed") {
            clearInterval(interval);
            setError(statusRes.active_job?.error_message || "Ingestion pipeline failed.");
            setIsUploading(false);
          } else if (attempts > 60) {
            clearInterval(interval);
            setIsUploading(false);
            onSuccess();
            onClose();
          }
        } catch (err: any) {
          clearInterval(interval);
          setError(err.message || "Failed to inspect project status");
          setIsUploading(false);
        }
      }, 1000);

    } catch (err: any) {
      setError(err.message || "Failed to create or upload project.");
      setIsUploading(false);
      setStatusMessage(null);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
      <div className="bg-[#161b22] border border-[#30363d] rounded-xl w-full max-w-lg shadow-2xl overflow-hidden animate-in fade-in zoom-in-95 duration-150">
        <div className="flex items-center justify-between px-6 py-4 border-b border-[#21262d]">
          <div className="flex items-center space-x-2 text-white font-semibold">
            <Upload className="w-5 h-5 text-brand-400" />
            <span>Upload Codebase</span>
          </div>
          {!isUploading && (
            <button
              onClick={onClose}
              className="text-[#8b949e] hover:text-white p-1 rounded transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          )}
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          {error && (
            <div className="p-3 bg-rose-500/10 border border-rose-500/30 rounded-lg text-rose-400 text-xs flex items-center space-x-2">
              <AlertCircle className="w-4 h-4 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          <div>
            <label className="block text-xs font-medium text-[#8b949e] mb-1.5">
              Project Name
            </label>
            <input
              type="text"
              required
              disabled={isUploading}
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. backend-api or auth-microservice"
              className="w-full bg-[#0d1117] border border-[#30363d] rounded-lg px-3.5 py-2 text-sm text-white placeholder-[#484f58] focus:outline-none focus:border-brand-500 disabled:opacity-50"
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-[#8b949e] mb-1.5">
              Source Code ZIP Archive
            </label>
            <label
              className={`flex flex-col items-center justify-center border-2 border-dashed rounded-xl p-6 transition-colors cursor-pointer ${
                selectedFile
                  ? "border-brand-500/50 bg-brand-500/5"
                  : "border-[#30363d] hover:border-[#8b949e] bg-[#0d1117]/50"
              } ${isUploading ? "opacity-50 pointer-events-none" : ""}`}
            >
              <input
                type="file"
                accept=".zip"
                disabled={isUploading}
                onChange={handleFileChange}
                className="hidden"
              />
              {selectedFile ? (
                <div className="text-center space-y-1.5">
                  <FileCode className="w-8 h-8 text-brand-400 mx-auto" />
                  <p className="text-sm font-medium text-white">{selectedFile.name}</p>
                  <p className="text-xs text-[#8b949e]">
                    {(selectedFile.size / (1024 * 1024)).toFixed(2)} MB
                  </p>
                </div>
              ) : (
                <div className="text-center space-y-1.5">
                  <Upload className="w-8 h-8 text-[#8b949e] mx-auto" />
                  <p className="text-sm text-[#c9d1d9]">Click or drag & drop repository ZIP</p>
                  <p className="text-xs text-[#8b949e]">Supports Python, JS, TS, Java, C/C++ (Max 50MB)</p>
                </div>
              )}
            </label>
          </div>

          {statusMessage && (
            <div className="p-3 bg-brand-500/10 border border-brand-500/20 rounded-lg text-brand-300 text-xs flex items-center space-x-2">
              <Loader2 className="w-4 h-4 animate-spin shrink-0 text-brand-400" />
              <span>{statusMessage}</span>
            </div>
          )}

          <div className="flex items-center justify-end space-x-3 pt-3 border-t border-[#21262d]">
            <button
              type="button"
              disabled={isUploading}
              onClick={onClose}
              className="px-4 py-2 text-xs font-medium text-[#8b949e] hover:text-white transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isUploading || !selectedFile}
              className="px-4 py-2 bg-brand-600 hover:bg-brand-500 disabled:opacity-50 text-white rounded-lg text-xs font-medium transition-colors flex items-center space-x-1.5"
            >
              {isUploading && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
              <span>{isUploading ? "Indexing Codebase..." : "Upload & Index"}</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
