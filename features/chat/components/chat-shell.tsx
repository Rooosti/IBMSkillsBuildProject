"use client";

import { motion } from "framer-motion";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { ChatHeader } from "@/features/chat/components/chat-header";
import { MessageList } from "@/features/chat/components/message-list";
import { ChatInput } from "@/features/chat/components/chat-input";
import { useChat } from "@/features/chat/hooks/use-chat";

type ChatShellProps = {
  isSignedIn: boolean;
};

export function ChatShell({ isSignedIn }: ChatShellProps) {
  const {
    input,
    setInput,
    messages,
    inputRef,
    placeholder,
    isSending,
    status,
    sendMessage,
  } = useChat({ isSignedIn });

  return (
    <div className="flex h-full w-full min-h-0 flex-col">
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.45 }}
        className="flex h-full w-full min-h-0 flex-1 flex-col"
      >
        <Card className="flex h-full w-full min-h-0 flex-col rounded-3xl bg-black/20">
          <CardHeader className="shrink-0">
            <ChatHeader isSignedIn={isSignedIn} status={status} />
          </CardHeader>

          <CardContent className="flex min-h-0 flex-1 flex-col p-0">
            <div className="flex-1 min-h-0 w-full">
              <MessageList messages={messages} />
            </div>

            <div className="shrink-0 px-4 pt-2 pb-4">
              <ChatInput
                ref={inputRef}
                value={input}
                onChange={setInput}
                onSend={sendMessage}
                placeholder={placeholder}
                disabled={!isSignedIn}
                isSending={isSending}
              />
            </div>
          </CardContent>
        </Card>
      </motion.div>
    </div>
  );
}
