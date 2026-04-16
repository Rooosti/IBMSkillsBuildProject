export type MessageRole = "assistant" | "user";

export type RecommendedGame = {
  steam_app_id: number;
  title: string;
  recommendation_score: number;
  short_description?: string;
  header_image_url?: string;
  store_url?: string;
  genres?: string[];
  tags?: string[];
  playtime_minutes?: number;
  is_owned?: boolean;
};

export type ChatMessage = {
  id: string;
  role: MessageRole;
  content: string;
  recommendations?: RecommendedGame[];
};

export type ChatRequest = {
  steam_id: string;
  conversation_id: number;
  message: string;
};

export type ChatConversation = {
  id: number;
  steam_id: string;
  title?: string | null;
};
