import React, { useState, useEffect, useRef } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  MessageSquare,
  Send,
  Plus,
  Loader2,
  Copy,
  Check,
  Terminal,
  Sparkles,
  AlertCircle,
  FileCode,
} from "lucide-react";
import { api } from "../services/api";
import { Citation, Message, Conversation } from "../types";
import { CitationBadge } from "../components/CitationBadge";

const SUGGESTED_QUESTIONS = [
  "Where is user authentication implemented?",
  "Explain how the database connection works.",
  "Which functions handle API requests?",
  "Explain the complete login flow.",
  "Where is password hashing performed?",
  "Which files should I inspect to understand the payment system?",
];

export const ChatPage: React.FC = () => {
  const { projectId } = useParams<{ projectId: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const [activeConversationId, setActiveConversationId] = useState<string | null>(null);
  const [inputMessage, setInputMessage] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [copiedId, setCopiedId] = useState<string | null>(null);

  const messagesEndRef = useRef<HTMLDivElement>(null);

  // 1. Fetch conversations list
  const { data: conversations = [], isLoading: convsLoading } = useQuery({
    queryKey: ["conversations", projectId],
    queryFn: () => (projectId ? api.listConversations(projectId) : Promise.resolve([])),
    enabled: !!projectId,
  });

  // 2. Fetch active conversation messages
  useEffect(() => {
    if (!activeConversationId) {
      setMessages([]);
      return;
    }

    api
      .getConversationMessages(activeConversationId)
      .then((detail) => setMessages(detail.messages))
      .catch((err) => console.error("Failed to load messages:", err));
  }, [activeConversationId]);

  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isSubmitting]);

  const handleSendMessage = async (queryText?: string) => {
    const textToSend = queryText || inputMessage;
    if (!textToSend.trim() || !projectId || isSubmitting) return;

    const userTempMessage: Message = {
      id: `temp-${Date.now()}`,
      conversation_id: activeConversationId || "",
      role: "user",
      content: textToSend.trim(),
      citations: [],
      created_at: new Date().toISOString(),
    };

    setMessages((prev) => [...prev, userTempMessage]);
    setInputMessage("");
    setIsSubmitting(true);

    try {
      const response = await api.chat(
        projectId,
        textToSend.trim(),
        activeConversationId || undefined,
        5,
        false
      );

      // If this was a new conversation, record ID and refresh sidebar
      if (!activeConversationId) {
        setActiveConversationId(response.conversation_id);
        queryClient.invalidateQueries({ queryKey: ["conversations", projectId] });
      }

      setMessages((prev) => [
        ...prev.filter((m) => m.id !== userTempMessage.id),
        userTempMessage,
        response.message,
      ]);
    } catch (err: any) {
      console.error("Chat error:", err);
      const errorMessage: Message = {
        id: `err-${Date.now()}`,
        conversation_id: activeConversationId || "",
        role: "assistant",
        content: `Error: ${err.message || "Failed to generate answer. Ensure the project is indexed."}`,
        citations: [],
        created_at: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleCitationClick = (citation: Citation) => {
    navigate(
      `/projects/${projectId}/explorer?file=${encodeURIComponent(citation.file_path)}&start=${citation.start_line}&end=${citation.end_line}`
    );
  };

  const copyToClipboard = (content: string, id: string) => {
    navigator.clipboard.writeText(content);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const startNewChat = () => {
    setActiveConversationId(null);
    setMessages([]);
  };

  return (
    <div className="flex h-[calc(100vh-53px)] overflow-hidden bg-[#0d1117]">
      {/* Left Sidebar: Conversations */}
      <div className="w-64 shrink-0 h-full bg-[#161b22] border-r border-[#21262d] flex flex-col select-none">
        <div className="p-3 border-b border-[#21262d]">
          <button
            onClick={startNewChat}
            className="w-full py-2 px-3 bg-brand-600/15 hover:bg-brand-600/25 text-brand-300 border border-brand-500/30 rounded-lg text-xs font-medium transition-colors flex items-center justify-center space-x-1.5"
          >
            <Plus className="w-3.5 h-3.5" />
            <span>New Chat</span>
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-2 space-y-1">
          {convsLoading ? (
            <div className="p-4 text-center text-[#8b949e]">
              <Loader2 className="w-4 h-4 animate-spin mx-auto mb-1 text-brand-400" />
              <span className="text-[11px]">Loading chats...</span>
            </div>
          ) : conversations.length === 0 ? (
            <div className="p-4 text-center text-[#8b949e] text-xs">
              No previous conversations
            </div>
          ) : (
            conversations.map((c) => {
              const isActive = c.id === activeConversationId;
              return (
                <button
                  key={c.id}
                  onClick={() => setActiveConversationId(c.id)}
                  className={`w-full text-left px-3 py-2 rounded-lg text-xs transition-colors flex items-center space-x-2 truncate ${
                    isActive
                      ? "bg-[#21262d] text-white font-medium border border-[#30363d]"
                      : "text-[#8b949e] hover:text-[#c9d1d9] hover:bg-[#21262d]/50"
                  }`}
                >
                  <MessageSquare className="w-3.5 h-3.5 shrink-0 text-brand-400" />
                  <span className="truncate">{c.title}</span>
                </button>
              );
            })
          )}
        </div>
      </div>

      {/* Main Chat Feed */}
      <div className="flex-1 flex flex-col h-full bg-[#0d1117]">
        {/* Messages Scroll Area */}
        <div className="flex-1 overflow-y-auto px-6 py-6 space-y-6 max-w-4xl w-full mx-auto">
          {messages.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full text-center py-12">
              <div className="w-12 h-12 bg-brand-600/10 border border-brand-500/20 text-brand-400 rounded-2xl flex items-center justify-center mb-4">
                <Sparkles className="w-6 h-6" />
              </div>
              <h2 className="text-xl font-semibold text-white tracking-tight">
                Ask anything about this codebase
              </h2>
              <p className="text-sm text-[#8b949e] max-w-md mt-1.5 mb-8">
                Questions are grounded in indexed source files with verified AST symbol boundaries and line numbers.
              </p>

              {/* Suggestions */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5 max-w-2xl w-full text-left">
                {SUGGESTED_QUESTIONS.map((q, idx) => (
                  <button
                    key={idx}
                    onClick={() => handleSendMessage(q)}
                    className="p-3 bg-[#161b22] hover:bg-[#21262d] border border-[#30363d] rounded-xl text-xs text-[#c9d1d9] hover:text-white transition-all text-left flex items-start space-x-2 group"
                  >
                    <Terminal className="w-4 h-4 text-brand-400 shrink-0 mt-0.5 group-hover:scale-110 transition-transform" />
                    <span>{q}</span>
                  </button>
                ))}
              </div>
            </div>
          ) : (
            messages.map((m) => {
              const isUser = m.role === "user";
              return (
                <div
                  key={m.id}
                  className={`flex items-start space-x-3 text-sm ${
                    isUser ? "justify-end" : "justify-start"
                  }`}
                >
                  {!isUser && (
                    <div className="w-8 h-8 rounded-lg bg-brand-600/15 border border-brand-500/30 text-brand-400 flex items-center justify-center shrink-0 mt-0.5">
                      <Terminal className="w-4 h-4" />
                    </div>
                  )}

                  <div
                    className={`max-w-2xl rounded-xl p-4 shadow-sm ${
                      isUser
                        ? "bg-brand-600 text-white rounded-tr-none"
                        : "bg-[#161b22] text-[#c9d1d9] border border-[#30363d] rounded-tl-none"
                    }`}
                  >
                    {/* Message Body */}
                    <div className="whitespace-pre-wrap leading-relaxed text-[13px] font-sans">
                      {m.content}
                    </div>

                    {/* Citations Footer */}
                    {!isUser && m.citations && m.citations.length > 0 && (
                      <div className="mt-4 pt-3 border-t border-[#21262d]">
                        <p className="text-[11px] font-medium text-[#8b949e] uppercase tracking-wider mb-2 flex items-center space-x-1">
                          <FileCode className="w-3 h-3 text-brand-400" />
                          <span>Source Citations</span>
                        </p>
                        <div className="flex flex-wrap gap-1.5">
                          {m.citations.map((c, cIdx) => (
                            <CitationBadge
                              key={cIdx}
                              citation={c}
                              onClick={handleCitationClick}
                            />
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Copy action for assistant */}
                    {!isUser && (
                      <div className="flex justify-end mt-2 pt-1">
                        <button
                          onClick={() => copyToClipboard(m.content, m.id)}
                          className="text-[#8b949e] hover:text-[#c9d1d9] text-xs inline-flex items-center space-x-1 p-1 rounded"
                          title="Copy response"
                        >
                          {copiedId === m.id ? (
                            <>
                              <Check className="w-3 h-3 text-emerald-400" />
                              <span className="text-[10px] text-emerald-400">Copied</span>
                            </>
                          ) : (
                            <>
                              <Copy className="w-3 h-3" />
                              <span className="text-[10px]">Copy</span>
                            </>
                          )}
                        </button>
                      </div>
                    )}
                  </div>
                </div>
              );
            })
          )}

          {isSubmitting && (
            <div className="flex items-start space-x-3 text-sm">
              <div className="w-8 h-8 rounded-lg bg-brand-600/15 border border-brand-500/30 text-brand-400 flex items-center justify-center shrink-0">
                <Loader2 className="w-4 h-4 animate-spin text-brand-400" />
              </div>
              <div className="bg-[#161b22] border border-[#30363d] rounded-xl rounded-tl-none p-4 text-[#8b949e] text-xs flex items-center space-x-2">
                <span>Retrieving relevant source chunks and generating grounded explanation...</span>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Input Bar */}
        <div className="p-4 border-t border-[#21262d] bg-[#161b22]">
          <form
            onSubmit={(e) => {
              e.preventDefault();
              handleSendMessage();
            }}
            className="max-w-4xl mx-auto flex items-center space-x-2"
          >
            <input
              type="text"
              value={inputMessage}
              disabled={isSubmitting}
              onChange={(e) => setInputMessage(e.target.value)}
              placeholder="Ask about functions, classes, auth, db, or request flows..."
              className="flex-1 bg-[#0d1117] border border-[#30363d] rounded-xl px-4 py-3 text-sm text-white placeholder-[#484f58] focus:outline-none focus:border-brand-500 disabled:opacity-50"
            />
            <button
              type="submit"
              disabled={isSubmitting || !inputMessage.trim()}
              className="p-3 bg-brand-600 hover:bg-brand-500 disabled:opacity-40 text-white rounded-xl transition-colors shrink-0"
            >
              {isSubmitting ? (
                <Loader2 className="w-5 h-5 animate-spin" />
              ) : (
                <Send className="w-5 h-5" />
              )}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
};
