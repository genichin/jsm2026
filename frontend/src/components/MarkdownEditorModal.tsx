"use client";

import { useEffect, useMemo, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Modal } from "./Modal";

interface MarkdownEditorModalProps {
  isOpen: boolean;
  title: string;
  value: string;
  onChange: (value: string) => void;
  onSubmit: (event: React.FormEvent<HTMLFormElement>) => void;
  onClose: () => void;
  isSubmitting?: boolean;
  submitLabel?: string;
  cancelLabel?: string;
  placeholder?: string;
  helperText?: string;
  initialTab?: "write" | "preview";
  size?: "sm" | "md" | "lg" | "xl";
  initialMode?: "view" | "edit"; // view: read-only, edit: write/preview
  enableEditToggle?: boolean; // if true, show edit button when in view mode
  onModeChange?: (mode: "view" | "edit") => void;
  editButtonLabel?: string;
}

const markdownComponents = {
  p: ({ node, ...props }: any) => <p className="my-2" {...props} />, // eslint-disable-line @typescript-eslint/no-unused-vars
  ul: ({ node, ...props }: any) => <ul className="my-2 ml-4 list-disc" {...props} />, // eslint-disable-line @typescript-eslint/no-unused-vars
  ol: ({ node, ...props }: any) => <ol className="my-2 ml-4 list-decimal" {...props} />, // eslint-disable-line @typescript-eslint/no-unused-vars
  li: ({ node, ...props }: any) => <li className="my-1" {...props} />, // eslint-disable-line @typescript-eslint/no-unused-vars
  code: ({ node, inline, ...props }: any) => // eslint-disable-line @typescript-eslint/no-unused-vars
    inline ? (
      <code className="bg-white px-2 py-1 rounded text-xs font-mono border border-gray-300" {...props} />
    ) : (
      <code className="bg-white p-2 rounded block text-xs font-mono my-2 overflow-x-auto border border-gray-300" {...props} />
    ),
  pre: ({ node, ...props }: any) => <pre className="bg-white p-3 rounded my-2 overflow-x-auto border border-gray-300" {...props} />, // eslint-disable-line @typescript-eslint/no-unused-vars
  blockquote: ({ node, ...props }: any) => <blockquote className="border-l-4 border-gray-400 pl-4 italic my-2 text-gray-700" {...props} />, // eslint-disable-line @typescript-eslint/no-unused-vars
  a: ({ node, ...props }: any) => <a className="text-blue-600 hover:text-blue-800 underline" {...props} />, // eslint-disable-line @typescript-eslint/no-unused-vars
  strong: ({ node, ...props }: any) => <strong className="font-semibold" {...props} />, // eslint-disable-line @typescript-eslint/no-unused-vars
  em: ({ node, ...props }: any) => <em className="italic" {...props} />, // eslint-disable-line @typescript-eslint/no-unused-vars
  h1: ({ node, ...props }: any) => <h1 className="text-lg font-bold my-2 mt-4" {...props} />, // eslint-disable-line @typescript-eslint/no-unused-vars
  h2: ({ node, ...props }: any) => <h2 className="text-base font-bold my-2 mt-3" {...props} />, // eslint-disable-line @typescript-eslint/no-unused-vars
  h3: ({ node, ...props }: any) => <h3 className="text-sm font-bold my-2 mt-2" {...props} />, // eslint-disable-line @typescript-eslint/no-unused-vars
};

export function MarkdownEditorModal({
  isOpen,
  title,
  value,
  onChange,
  onSubmit,
  onClose,
  isSubmitting = false,
  submitLabel,
  cancelLabel = "취소",
  placeholder,
  helperText,
  initialTab = "write",
  size = "xl",
  initialMode = "edit",
  enableEditToggle = true,
  onModeChange,
  editButtonLabel = "편집",
}: MarkdownEditorModalProps) {
  const [activeTab, setActiveTab] = useState<"write" | "preview">(initialTab);
  const [mode, setMode] = useState<"view" | "edit">(initialMode);

  useEffect(() => {
    if (isOpen) {
      setActiveTab(initialTab);
      setMode(initialMode);
    }
  }, [isOpen, initialTab, initialMode]);

  const previewContent = useMemo(() => value.trim(), [value]);

  function switchToEdit() {
    setMode("edit");
    setActiveTab("write");
    onModeChange?.("edit");
  }

  const headerActions = enableEditToggle && mode === "view"
    ? (
        <button
          type="button"
          onClick={switchToEdit}
          className="text-sm px-3 py-1 rounded border border-gray-300 hover:bg-gray-100"
        >
          {editButtonLabel}
        </button>
      )
    : undefined;

  return (
    <Modal isOpen={isOpen} onClose={onClose} title={title} size={size} titleActions={headerActions}>
      {mode === "view" ? (
        <div className="space-y-4">
          <div className="border rounded p-4 bg-gray-50 min-h-[400px]">
            {previewContent ? (
              <div className="prose prose-sm max-w-none">
                <ReactMarkdown remarkPlugins={[remarkGfm]} components={markdownComponents as any}>
                  {previewContent}
                </ReactMarkdown>
              </div>
            ) : (
              <p className="text-gray-400 text-center py-20">작성한 내용이 여기 표시됩니다</p>
            )}
          </div>
          <div className="flex justify-end">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 rounded bg-gray-200 hover:bg-gray-300"
            >
              {cancelLabel}
            </button>
          </div>
        </div>
      ) : (
        <form onSubmit={onSubmit} className="space-y-4">
          <div className="flex gap-2 border-b">
            <button
              type="button"
              onClick={() => setActiveTab("write")}
              className={`px-4 py-2 font-medium text-sm border-b-2 transition-colors ${
                activeTab === "write"
                  ? "text-blue-600 border-blue-600"
                  : "text-gray-600 border-transparent hover:text-gray-800"
              }`}
            >
              작성
            </button>
            <button
              type="button"
              onClick={() => setActiveTab("preview")}
              className={`px-4 py-2 font-medium text-sm border-b-2 transition-colors ${
                activeTab === "preview"
                  ? "text-blue-600 border-blue-600"
                  : "text-gray-600 border-transparent hover:text-gray-800"
              }`}
            >
              미리보기
            </button>
          </div>

          {activeTab === "write" && (
            <div className="space-y-2">
              <textarea
                value={value}
                onChange={(e) => onChange(e.target.value)}
                placeholder={placeholder}
                className="w-full border rounded px-3 py-2 min-h-[400px] focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
              {helperText && <p className="text-xs text-gray-500">{helperText}</p>}
            </div>
          )}

          {activeTab === "preview" && (
            <div className="border rounded p-4 bg-gray-50 min-h-[400px]">
              {previewContent ? (
                <div className="prose prose-sm max-w-none">
                  <ReactMarkdown remarkPlugins={[remarkGfm]} components={markdownComponents as any}>
                    {previewContent}
                  </ReactMarkdown>
                </div>
              ) : (
                <p className="text-gray-400 text-center py-20">작성한 내용이 여기 표시됩니다</p>
              )}
            </div>
          )}

          <div className="flex justify-end gap-2">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 rounded bg-gray-200 hover:bg-gray-300"
            >
              {cancelLabel}
            </button>
            <button
              type="submit"
              disabled={!previewContent || isSubmitting}
              className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isSubmitting ? submitLabel ?? "작성 중..." : submitLabel ?? "작성"}
            </button>
          </div>
        </form>
      )}
    </Modal>
  );
}
