import { env } from "@/lib/config/env";

export type RecommendationQueryRequest = {
  userId: string;
  query: string;
  mode: "discovery" | "library" | "party";
};

export type RecommendationResult = {
  game_id: string;
  title: string;
  score: number;
  reasons: string[];
};

export type RecommendationQueryResponse = {
  parsed_query: Record<string, unknown>;
  results: RecommendationResult[];
};

export async function postRecommendationQuery(
  payload: RecommendationQueryRequest
): Promise<RecommendationQueryResponse> {
  const response = await fetch(`${env.apiBaseUrl}/recommendations/query`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    throw new Error("Failed to fetch recommendations");
  }

  return response.json();
}
