import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

interface ChatMarkdownProps {
  content: string;
}

export function ChatMarkdown({ content }: ChatMarkdownProps) {
  return (
    <div className="min-w-0 space-y-3 break-words text-sm leading-7 text-slate-200">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        skipHtml
        components={{
          h1: ({ children }) => (
            <h1 className="mt-4 text-xl font-bold text-white">
              {children}
            </h1>
          ),
          h2: ({ children }) => (
            <h2 className="mt-4 text-lg font-semibold text-white">
              {children}
            </h2>
          ),
          h3: ({ children }) => (
            <h3 className="mt-3 font-semibold text-white">
              {children}
            </h3>
          ),
          ul: ({ children }) => (
            <ul className="list-disc space-y-1 pl-6">
              {children}
            </ul>
          ),
          ol: ({ children }) => (
            <ol className="list-decimal space-y-1 pl-6">
              {children}
            </ol>
          ),
          pre: ({ children }) => (
            <pre className="overflow-x-auto rounded-xl border border-slate-700 bg-slate-950 p-4 text-xs">
              {children}
            </pre>
          ),
          code: ({ children }) => (
            <code className="rounded bg-slate-800 px-1 py-0.5 font-mono text-sky-300">
              {children}
            </code>
          ),
          blockquote: ({ children }) => (
            <blockquote className="border-l-4 border-blue-500 pl-4 text-slate-400">
              {children}
            </blockquote>
          ),
          table: ({ children }) => (
            <div className="overflow-x-auto">
              <table className="w-full border-collapse text-left text-sm">
                {children}
              </table>
            </div>
          ),
          th: ({ children }) => (
            <th className="border border-slate-700 bg-slate-800 p-3">
              {children}
            </th>
          ),
          td: ({ children }) => (
            <td className="border border-slate-700 p-3">
              {children}
            </td>
          ),
          a: ({ children }) => (
            <span className="text-sky-300 underline">
              {children}
            </span>
          ),
          img: () => null,
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}
