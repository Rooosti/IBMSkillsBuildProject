"use client";

import { AnimatePresence, motion } from "framer-motion";
import { ScrollArea, ScrollBar } from "@/components/ui/scroll-area";
import { MessageBubble } from "@/features/chat/components/message-bubble";
import type { ChatMessage } from "@/features/chat/types";

type MessageListProps = {
  messages: ChatMessage[];
};

const listVariants = {
  hidden: {},
  visible: {
    transition: {
      staggerChildren: 0.06,
    },
  },
};

export function MessageList({ messages }: MessageListProps) {
  return (
    <ScrollArea className="h-full w-full">
      <div className="flex h-full w-full flex-col">
        <motion.div
          variants={listVariants}
          initial="hidden"
          animate="visible"
          className="mx-auto flex w-full max-w-3xl flex-col gap-8 px-4 py-6 sm:px-6"
        >
          <AnimatePresence initial={false}>
            {messages.map((message) => (
              <MessageBubble key={message.id} message={message} />
            ))}
          </AnimatePresence>
        </motion.div>
      </div>
      <ScrollBar orientation="vertical" />
    </ScrollArea>
  );
}
