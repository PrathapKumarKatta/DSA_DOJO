import React from "react";
import { FileCode, ExternalLink } from "lucide-react";
import { Citation } from "../types";

interface CitationBadgeProps {
  citation: Citation;
  onClick?: (citation: Citation) => void;
}

export const CitationBadge: React.FC<CitationBadgeProps> = ({ citation, onClick }) => {
  const fileName = citation.file_path.split("/").pop() || citation.file_path;

  return (
    <button
      type="button"
      onClick={() => onClick && onClick(citation)}
      className="inline-flex items-center space-x-1.5 px-2.5 py-1 rounded-md bg-[#21262d] hover:bg-[#30363d] border border-[#30363d] hover:border-brand-500/50 text-xs text-brand-300 transition-colors group cursor-pointer text-left"
    >
      <FileCode className="w-3.5 h-3.5 text-brand-400 group-hover:scale-105 transition-transform" />
      <span className="font-mono font-medium truncate max-w-[200px]" title={citation.file_path}>
        {fileName}
      </span>
      <span className="text-[#8b949e] text-[11px] font-mono">
        :{citation.start_line}–{citation.end_line}
      </span>
      <ExternalLink className="w-3 h-3 text-[#8b949e] group-hover:text-brand-400 ml-0.5" />
    </button>
  );
};
