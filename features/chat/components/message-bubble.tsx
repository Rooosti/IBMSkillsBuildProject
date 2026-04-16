"use client";

import { motion } from "framer-motion";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { RecommendationsList } from "./recommendations-list";
import type { ChatMessage } from "@/features/chat/types";

type MessageBubbleProps = {
  message: ChatMessage;
};

export function MessageBubble({ message }: MessageBubbleProps) {
  const isUser = message.role === "user";

  return (
    <motion.div
      initial={{
        opacity: 0,
        y: 14,
        x: isUser ? 10 : -10,
        scale: 0.94,
      }}
      animate={{
        opacity: 1,
        y: 0,
        x: 0,
        scale: 1,
      }}
      exit={{
        opacity: 0,
        y: 6,
        scale: 0.98,
      }}
      transition={{
        type: "spring",
        stiffness: 420,
        damping: 22,
        mass: 0.75,
      }}
      className={`rounded-3xl px-4 py-3 text-sm leading-6 overflow-hidden min-w-0 ${
        isUser
          ? "max-w-[60%] ml-auto bg-zinc-100 text-zinc-900"
          : "max-w-[90%] mr-auto bg-black/25 text-zinc-200"
      }`}
    >
      {isUser ? (
        <div className="whitespace-pre-wrap">{message.content}</div>
      ) : (
        <div className="flex flex-col">
          <div className="prose prose-invert prose-sm max-w-none prose-p:my-2 prose-ul:my-2 prose-ol:my-2 prose-li:my-1 prose-strong:text-zinc-100 prose-code:text-zinc-100 prose-pre:bg-black/30 prose-pre:border prose-pre:border-zinc-700/50">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
              {message.content}
            </ReactMarkdown>
          </div>
          {message.recommendations && message.recommendations.length > 0 && (
            <RecommendationsList recommendations={message.recommendations} />
          )}
        </div>
      )}
    </motion.div>
  );
}
