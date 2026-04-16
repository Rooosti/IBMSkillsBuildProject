"use client";

import { useCallback, useMemo, useRef, useState } from "react";
import { createConversation, postChatMessage } from "@/lib/api/client";
import type { ChatMessage } from "@/features/chat/types";

type UseChatOptions = {
  isSignedIn: boolean;
};

export function useChat({ isSignedIn }: UseChatOptions) {
  const [input, setInput] = useState("");
  const [isSending, setIsSending] = useState(false);
  const [status, setStatus] = useState<string>("ready");
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [conversationId, setConversationId] = useState<number | null>(null);

  const inputRef = useRef<HTMLInputElement | null>(null);

  const placeholder = useMemo(() => {
    if (!isSignedIn) return "Connect Steam to start chatting";
    return "Ask about your library or what to play next...";
  }, [isSignedIn]);

  const focusInput = useCallback(() => {
    window.setTimeout(() => {
      inputRef.current?.focus();
    }, 0);
  }, []);

  const ensureConversation = useCallback(async (): Promise<number> => {
    if (conversationId !== null) return conversationId;

    const created = await createConversation();
    setConversationId(created.conversation_id);
    return created.conversation_id;
  }, [conversationId]);

  const sendMessage = useCallback(async () => {
    const trimmed = input.trim();
    if (!trimmed || !isSignedIn || isSending) return;

    const userMessage: ChatMessage = {
      id: `user-${Date.now()}`,
      role: "user",
      content: trimmed,
    };

    setMessages((current) => [...current, userMessage]);
    setInput("");
    setIsSending(true);
    setStatus("connecting...");
    focusInput();

    try {
      const cid = await ensureConversation();

      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/v1/chat`,
        {
          method: "POST",
          credentials: "include",
          headers: {
            "Content-Type": "application/json",
            Accept: "text/event-stream",
          },
          body: JSON.stringify({
            conversation_id: cid,
            message: trimmed,
          }),
        }
      );

      if (!response.ok) {
        const errorText = await response.text().catch(() => "");
        throw new Error(
          `Chat request failed: ${response.status} ${response.statusText}${
            errorText ? ` - ${errorText}` : ""
          }`
        );
      }

      if (!response.body) {
        throw new Error("Chat response did not include a readable stream body");
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let finalReply = "";
      let recommendations: any[] = [];
      let buffer = "";

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() || ""; // Keep the last partial line in the buffer

        for (const line of lines) {
          const trimmed = line.trim();
          if (!trimmed || !trimmed.startsWith("data: ")) continue;

          try {
            const dataStr = trimmed.slice(6);
            if (!dataStr) continue;
            const payload = JSON.parse(dataStr);
            
            if (payload.status) {
              console.log("Status update:", payload.status); // Adding log for debugging
              setStatus(payload.status);
            }
            if (payload.reply) {
              finalReply = payload.reply;
            }
            if (payload.recommendations) {
              recommendations = payload.recommendations;
            }
            if (payload.error) {
              throw new Error(payload.error);
            }
          } catch (e) {
            console.warn("Failed to parse SSE payload", e, line);
          }
        }
      }

      const assistantMessage: ChatMessage = {
        id: `assistant-${Date.now()}`,
        role: "assistant",
        content: finalReply || "I could not generate a reply.",
        recommendations: recommendations.length > 0 ? recommendations : undefined,
      };

      setMessages((current) => [...current, assistantMessage]);
    } catch (err) {
      console.error(err);
      const assistantMessage: ChatMessage = {
        id: `assistant-${Date.now()}`,
        role: "assistant",
        content:
          "It seems the chat agent was unable to connect. Please try again later.",
      };

      setMessages((current) => [...current, assistantMessage]);
    } finally {
      setIsSending(false);
      setStatus("ready");
      focusInput();
    }
  }, [ensureConversation, focusInput, input, isSending, isSignedIn]);

  return {
    input,
    setInput,
    messages,
    inputRef,
    placeholder,
    isSending,
    status,
    sendMessage,
    conversationId,
  };
}
