import React, { useState, useEffect } from "react";
import { useParams, useSearchParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { Loader2, Search, AlertCircle, FileCode } from "lucide-react";
import { api } from "../services/api";
import { SourceFile, SourceFileDetail } from "../types";
import { FileTree } from "../components/FileTree";
import { CodeViewer } from "../components/CodeViewer";

export const ProjectExplorerPage: React.FC = () => {
  const { projectId } = useParams<{ projectId: string }>();
  const [searchParams, setSearchParams] = useSearchParams();

  const [selectedFileId, setSelectedFileId] = useState<string | null>(null);
  const [selectedFileDetail, setSelectedFileDetail] = useState<SourceFileDetail | null>(null);
  const [highlightRange, setHighlightRange] = useState<{ startLine: number; endLine: number } | null>(null);

  // Fetch file list
  const { data: fileData, isLoading: filesLoading } = useQuery({
    queryKey: ["project_files", projectId],
    queryFn: () => (projectId ? api.listFiles(projectId) : Promise.reject("No project id")),
    enabled: !!projectId,
  });

  const files = fileData?.items || [];

  // Handle URL query parameters (e.g. from citation badge click)
  useEffect(() => {
    if (!files.length) return;

    const queryFilePath = searchParams.get("file");
    const start = searchParams.get("start");
    const end = searchParams.get("end");

    if (queryFilePath) {
      const match = files.find((f) => f.path === queryFilePath || f.path.endsWith(queryFilePath));
      if (match) {
        setSelectedFileId(match.id);
        if (start && end) {
          setHighlightRange({ startLine: parseInt(start, 10), endLine: parseInt(end, 10) });
        }
      }
    } else if (!selectedFileId && files.length > 0) {
      setSelectedFileId(files[0].id);
    }
  }, [files, searchParams]);

  // Fetch full content when selected file changes
  useEffect(() => {
    if (!projectId || !selectedFileId) return;

    api
      .getFileDetail(projectId, selectedFileId)
      .then((detail) => setSelectedFileDetail(detail))
      .catch((err) => console.error("Failed to load file detail:", err));
  }, [projectId, selectedFileId]);

  const handleSelectFile = (file: SourceFile) => {
    setSelectedFileId(file.id);
    setHighlightRange(null);
    setSearchParams({ file: file.path });
  };

  return (
    <div className="flex h-[calc(100vh-53px)] overflow-hidden bg-[#0d1117]">
      {/* Left Sidebar: File Tree */}
      <div className="w-80 shrink-0 h-full">
        {filesLoading ? (
          <div className="flex items-center justify-center h-full text-[#8b949e]">
            <Loader2 className="w-5 h-5 animate-spin mr-2" />
            <span className="text-xs">Loading tree...</span>
          </div>
        ) : (
          <FileTree
            files={files}
            selectedFileId={selectedFileId}
            onSelectFile={handleSelectFile}
          />
        )}
      </div>

      {/* Right Pane: Monaco Code Viewer */}
      <div className="flex-1 h-full min-w-0">
        <CodeViewer
          file={selectedFileDetail}
          highlightRange={highlightRange}
        />
      </div>
    </div>
  );
};
