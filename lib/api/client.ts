import { env } from "@/lib/config/env";

const API_BASE_URL =
  env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";

export type ChatRequest = {
  conversation_id: number;
  message: string;
};

export type ChatResponse = {
  reply: string;
};

export type PostChatMessageRequest = {
  conversation_id: number;
  message: string;
};

export type PostChatMessageResponse = {
  reply: string;
};

export type CreateConversationResponse = {
  conversation_id: number;
  steam_id: string;
};

export async function createConversation(): Promise<CreateConversationResponse> {
  const response = await fetch(`${API_BASE_URL}/conversations`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    credentials: "include",
  });

  if (!response.ok) {
    throw new Error("Failed to create conversation");
  }

  return response.json();
}

export async function postChatMessage(
  payload: PostChatMessageRequest
): Promise<PostChatMessageResponse> {
  const response = await fetch(`${API_BASE_URL}/chat`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    credentials: "include",
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    throw new Error("Failed to send chat message");
  }

  return response.json();
}
