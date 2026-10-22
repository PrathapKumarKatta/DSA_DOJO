import React, { useState, useMemo } from "react";
import { Search, FileCode, Folder, ChevronRight, ChevronDown } from "lucide-react";
import { SourceFile } from "../types";

interface FileTreeProps {
  files: SourceFile[];
  selectedFileId: string | null;
  onSelectFile: (file: SourceFile) => void;
}

export const FileTree: React.FC<FileTreeProps> = ({
  files,
  selectedFileId,
  onSelectFile,
}) => {
  const [filterQuery, setFilterQuery] = useState("");

  const filteredFiles = useMemo(() => {
    if (!filterQuery.trim()) return files;
    const q = filterQuery.toLowerCase();
    return files.filter((f) => f.path.toLowerCase().includes(q));
  }, [files, filterQuery]);

  return (
    <div className="flex flex-col h-full bg-[#161b22] border-r border-[#21262d] select-none text-xs">
      {/* Search Header */}
      <div className="p-3 border-b border-[#21262d]">
        <div className="relative">
          <Search className="w-3.5 h-3.5 absolute left-2.5 top-1/2 -translate-y-1/2 text-[#8b949e]" />
          <input
            type="text"
            placeholder="Search files..."
            value={filterQuery}
            onChange={(e) => setFilterQuery(e.target.value)}
            className="w-full bg-[#0d1117] border border-[#30363d] rounded-md pl-8 pr-3 py-1.5 text-xs text-[#c9d1d9] placeholder-[#484f58] focus:outline-none focus:border-brand-500"
          />
        </div>
      </div>

      {/* Files List */}
      <div className="flex-1 overflow-y-auto p-2 space-y-0.5">
        {filteredFiles.length === 0 ? (
          <div className="p-4 text-center text-[#8b949e]">
            {filterQuery ? "No matching files" : "No files indexed yet"}
          </div>
        ) : (
          filteredFiles.map((file) => {
            const isSelected = file.id === selectedFileId;
            const fileName = file.path.split("/").pop() || file.path;
            const dirPath = file.path.includes("/")
              ? file.path.substring(0, file.path.lastIndexOf("/"))
              : "";

            return (
              <button
                key={file.id}
                onClick={() => onSelectFile(file)}
                className={`w-full flex items-center justify-between px-2.5 py-1.5 rounded-md text-left transition-colors group ${
                  isSelected
                    ? "bg-brand-600/20 text-brand-300 font-medium border border-brand-500/30"
                    : "text-[#8b949e] hover:text-[#c9d1d9] hover:bg-[#21262d]/60"
                }`}
              >
                <div className="flex items-center space-x-2 truncate min-w-0">
                  <FileCode className={`w-3.5 h-3.5 shrink-0 ${isSelected ? "text-brand-400" : "text-[#8b949e]"}`} />
                  <div className="truncate">
                    <span className="text-[#c9d1d9]">{fileName}</span>
                    {dirPath && (
                      <span className="text-[#484f58] ml-1.5 text-[10px]">
                        {dirPath}
                      </span>
                    )}
                  </div>
                </div>
                <span className="text-[10px] text-[#484f58] shrink-0 ml-2">
                  {file.line_count}L
                </span>
              </button>
            );
          })
        )}
      </div>

      <div className="px-3 py-2 border-t border-[#21262d] text-[11px] text-[#484f58] flex justify-between">
        <span>{filteredFiles.length} files</span>
        <span>AST Indexed</span>
      </div>
    </div>
  );
};
