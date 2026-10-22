import React, { useEffect, useRef } from "react";
import Editor, { OnMount } from "@monaco-editor/react";
import { SourceFileDetail } from "../types";

interface CodeViewerProps {
  file: SourceFileDetail | null;
  highlightRange?: { startLine: number; endLine: number } | null;
}

const LANGUAGE_MAP: Record<string, string> = {
  python: "python",
  javascript: "javascript",
  typescript: "typescript",
  java: "java",
  c: "c",
  cpp: "cpp",
  json: "json",
  markdown: "markdown",
  sql: "sql",
  yaml: "yaml",
  bash: "shell",
  text: "plaintext",
};

export const CodeViewer: React.FC<CodeViewerProps> = ({ file, highlightRange }) => {
  const editorRef = useRef<any>(null);
  const decorationsRef = useRef<string[]>([]);

  const handleEditorMount: OnMount = (editor, monaco) => {
    editorRef.current = editor;

    // Define custom decoration CSS if needed
    monaco.editor.defineTheme("codebase-dark", {
      base: "vs-dark",
      inherit: true,
      rules: [],
      colors: {
        "editor.background": "#0d1117",
        "editor.lineHighlightBackground": "#161b22",
        "editorLineNumber.foreground": "#484f58",
        "editorLineNumber.activeForeground": "#c9d1d9",
      },
    });
    monaco.editor.setTheme("codebase-dark");

    applyHighlight();
  };

  const applyHighlight = () => {
    if (!editorRef.current || !highlightRange) return;

    const editor = editorRef.current;
    const { startLine, endLine } = highlightRange;

    // Remove old decorations
    decorationsRef.current = editor.deltaDecorations(decorationsRef.current, [
      {
        range: {
          startLineNumber: startLine,
          startColumn: 1,
          endLineNumber: endLine,
          endColumn: 1000,
        },
        options: {
          isWholeLine: true,
          className: "bg-brand-600/25 border-l-4 border-brand-400",
          overviewRuler: {
            color: "#38bdf8",
            position: 1,
          },
        },
      },
    ]);

    // Jump to line
    editor.revealLineInCenter(startLine);
  };

  useEffect(() => {
    applyHighlight();
  }, [highlightRange, file]);

  if (!file) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-[#8b949e] p-8 text-center bg-[#0d1117]">
        <p className="text-sm">Select a file from the explorer or click a citation in chat</p>
      </div>
    );
  }

  const monacoLanguage = LANGUAGE_MAP[file.language] || "plaintext";

  return (
    <div className="flex flex-col h-full bg-[#0d1117]">
      {/* File Header */}
      <div className="flex items-center justify-between px-4 py-2 bg-[#161b22] border-b border-[#21262d] text-xs">
        <div className="flex items-center space-x-2 text-[#c9d1d9]">
          <span className="font-mono">{file.path}</span>
          {highlightRange && (
            <span className="px-2 py-0.5 bg-brand-500/20 text-brand-300 border border-brand-500/30 rounded text-[10px]">
              Cited: Lines {highlightRange.startLine}–{highlightRange.endLine}
            </span>
          )}
        </div>
        <div className="flex items-center space-x-3 text-[#8b949e] text-[11px]">
          <span>{file.language}</span>
          <span>{file.line_count} lines</span>
        </div>
      </div>

      {/* Monaco Container */}
      <div className="flex-1 overflow-hidden">
        <Editor
          height="100%"
          language={monacoLanguage}
          value={file.content}
          theme="vs-dark"
          onMount={handleEditorMount}
          options={{
            readOnly: true,
            minimap: { enabled: true },
            fontSize: 13,
            lineNumbers: "on",
            scrollBeyondLastLine: false,
            fontFamily: "'JetBrains Mono', monospace",
            wordWrap: "on",
            automaticLayout: true,
            renderWhitespace: "selection",
          }}
        />
      </div>
    </div>
  );
};
