import React, { useState } from "react";
import { Link } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  FolderGit2,
  Plus,
  Code2,
  MessageSquare,
  Trash2,
  FileCode,
  Layers,
  Clock,
  CheckCircle2,
  AlertCircle,
  Loader2,
} from "lucide-react";
import { api } from "../services/api";
import { Project } from "../types";
import { ProjectUploadModal } from "../components/ProjectUploadModal";

export const DashboardPage: React.FC = () => {
  const queryClient = useQueryClient();
  const [isUploadModalOpen, setIsUploadModalOpen] = useState(false);

  const { data, isLoading, error } = useQuery({
    queryKey: ["projects"],
    queryFn: api.listProjects,
    refetchInterval: 5000, // Poll to catch background ingestion status changes
  });

  const deleteMutation = useMutation({
    mutationFn: api.deleteProject,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["projects"] });
    },
  });

  const handleDelete = (projectId: string, projectName: string) => {
    if (confirm(`Are you sure you want to delete project "${projectName}"? All indexed vectors will be permanently removed.`)) {
      deleteMutation.mutate(projectId);
    }
  };

  const getStatusBadge = (status: Project["status"]) => {
    switch (status) {
      case "ready":
        return (
          <span className="inline-flex items-center space-x-1 px-2.5 py-0.5 rounded-full text-xs font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
            <CheckCircle2 className="w-3 h-3" />
            <span>Ready</span>
          </span>
        );
      case "processing":
        return (
          <span className="inline-flex items-center space-x-1 px-2.5 py-0.5 rounded-full text-xs font-medium bg-amber-500/10 text-amber-400 border border-amber-500/20">
            <Loader2 className="w-3 h-3 animate-spin" />
            <span>Indexing...</span>
          </span>
        );
      case "failed":
        return (
          <span className="inline-flex items-center space-x-1 px-2.5 py-0.5 rounded-full text-xs font-medium bg-rose-500/10 text-rose-400 border border-rose-500/20">
            <AlertCircle className="w-3 h-3" />
            <span>Failed</span>
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center space-x-1 px-2.5 py-0.5 rounded-full text-xs font-medium bg-zinc-500/10 text-zinc-400 border border-zinc-500/20">
            <Clock className="w-3 h-3" />
            <span>Created</span>
          </span>
        );
    }
  };

  return (
    <div className="max-w-7xl mx-auto px-6 py-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 pb-6 border-b border-[#21262d]">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight">Codebase Repositories</h1>
          <p className="text-sm text-[#8b949e] mt-1">
            Upload repository ZIPs to index symbols, extract AST chunks, and query architecture with AI.
          </p>
        </div>
        <button
          onClick={() => setIsUploadModalOpen(true)}
          className="px-4 py-2 bg-brand-600 hover:bg-brand-500 text-white rounded-lg text-xs font-medium transition-colors flex items-center space-x-2 shrink-0 shadow-sm"
        >
          <Plus className="w-4 h-4" />
          <span>Upload Codebase</span>
        </button>
      </div>

      {/* Content */}
      <div className="mt-8">
        {isLoading ? (
          <div className="flex flex-col items-center justify-center p-16 text-[#8b949e]">
            <Loader2 className="w-8 h-8 animate-spin text-brand-400 mb-3" />
            <p className="text-sm">Loading projects...</p>
          </div>
        ) : error ? (
          <div className="p-4 bg-rose-500/10 border border-rose-500/20 rounded-xl text-rose-400 text-sm flex items-center space-x-2">
            <AlertCircle className="w-5 h-5 shrink-0" />
            <span>Failed to load projects: {(error as any).message}</span>
          </div>
        ) : data?.items.length === 0 ? (
          <div className="border border-dashed border-[#30363d] rounded-2xl p-12 text-center bg-[#161b22]/30">
            <div className="w-12 h-12 bg-brand-600/10 border border-brand-500/20 rounded-xl text-brand-400 flex items-center justify-center mx-auto mb-4">
              <FolderGit2 className="w-6 h-6" />
            </div>
            <h3 className="text-base font-semibold text-white">No codebases indexed yet</h3>
            <p className="text-sm text-[#8b949e] max-w-md mx-auto mt-1.5 mb-6">
              Upload a .zip archive of any Python, JavaScript, TypeScript, Java, or C/C++ project to begin analysis.
            </p>
            <button
              onClick={() => setIsUploadModalOpen(true)}
              className="px-4 py-2 bg-brand-600 hover:bg-brand-500 text-white rounded-lg text-xs font-medium transition-colors inline-flex items-center space-x-2"
            >
              <Plus className="w-4 h-4" />
              <span>Upload First Project</span>
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
            {data?.items.map((project) => (
              <div
                key={project.id}
                className="bg-[#161b22] border border-[#30363d] hover:border-[#8b949e]/40 rounded-xl p-5 shadow-sm transition-all flex flex-col justify-between group"
              >
                <div>
                  <div className="flex items-start justify-between gap-3 mb-3">
                    <h3 className="font-semibold text-white text-base truncate group-hover:text-brand-400 transition-colors">
                      {project.name}
                    </h3>
                    {getStatusBadge(project.status)}
                  </div>

                  <div className="grid grid-cols-2 gap-2 my-4 py-3 border-y border-[#21262d] text-xs">
                    <div className="flex items-center space-x-2 text-[#8b949e]">
                      <FileCode className="w-3.5 h-3.5 text-brand-400" />
                      <span>{project.file_count} files</span>
                    </div>
                    <div className="flex items-center space-x-2 text-[#8b949e]">
                      <Layers className="w-3.5 h-3.5 text-brand-400" />
                      <span>{project.chunk_count} chunks</span>
                    </div>
                  </div>
                </div>

                <div className="flex items-center justify-between pt-2">
                  <div className="flex items-center space-x-2">
                    <Link
                      to={`/projects/${project.id}/explorer`}
                      className="px-2.5 py-1.5 bg-[#21262d] hover:bg-[#30363d] text-[#c9d1d9] hover:text-white rounded-md text-xs font-medium transition-colors flex items-center space-x-1.5"
                    >
                      <Code2 className="w-3.5 h-3.5" />
                      <span>Explorer</span>
                    </Link>
                    <Link
                      to={`/projects/${project.id}/chat`}
                      className="px-2.5 py-1.5 bg-brand-600/20 hover:bg-brand-600/30 text-brand-300 rounded-md text-xs font-medium transition-colors flex items-center space-x-1.5 border border-brand-500/30"
                    >
                      <MessageSquare className="w-3.5 h-3.5" />
                      <span>AI Chat</span>
                    </Link>
                  </div>

                  <button
                    onClick={() => handleDelete(project.id, project.name)}
                    className="p-1.5 text-[#8b949e] hover:text-rose-400 hover:bg-[#21262d] rounded transition-colors"
                    title="Delete project"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      <ProjectUploadModal
        isOpen={isUploadModalOpen}
        onClose={() => setIsUploadModalOpen(false)}
        onSuccess={() => queryClient.invalidateQueries({ queryKey: ["projects"] })}
      />
    </div>
  );
};
