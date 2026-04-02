import { base } from '$app/paths';

const BASE = base;

export interface Conversation {
  id: string;
  title: string | null;
  mode: string;
  pinned: number;
  folder: string | null;
  created_at: string;
  updated_at: string;
}

export interface Message {
  id: string;
  role: 'user' | 'conservative' | 'liberal' | 'consensus';
  content: string;
  risk_level?: string;
  cited_articles?: string;
  created_at: string;
}

export async function createConversation(mode: string): Promise<{ id: string }> {
  const res = await fetch(`${BASE}/api/conversations`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ mode }),
  });
  return res.json();
}

export async function listConversations(): Promise<Conversation[]> {
  const res = await fetch(`${BASE}/api/conversations`);
  return res.json();
}

export async function getConversation(
  id: string
): Promise<{ conversation: Conversation; messages: Message[] }> {
  const res = await fetch(`${BASE}/api/conversations/${id}`);
  return res.json();
}

export async function deleteConversation(id: string): Promise<void> {
  await fetch(`${BASE}/api/conversations/${id}`, { method: 'DELETE' });
}

export async function updateConversation(id: string, data: { pinned?: boolean; folder?: string }): Promise<void> {
  await fetch(`${BASE}/api/conversations/${id}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
}

export async function submitFeedback(data: {
  conversation_id: string;
  user_question: string;
  bot_response: string;
  risk_level: string | null;
  rating: 'up' | 'down';
}): Promise<void> {
  await fetch(`${BASE}/api/feedback`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
}

export interface SSECallbacks {
  onConservativeStart: () => void;
  onConservativeToken: (token: string) => void;
  onConservativeEnd: (data: { cited_articles: string[] }) => void;
  onLiberalStart: () => void;
  onLiberalToken: (token: string) => void;
  onLiberalEnd: (data: { cited_articles: string[] }) => void;
  onConsensus: (data: {
    content: string;
    risk_level: string;
    cited_articles: string[];
    request_feedback: boolean;
  }) => void;
}

export function streamChat(
  conversationId: string,
  question: string,
  callbacks: SSECallbacks
): AbortController {
  const controller = new AbortController();

  fetch(`${BASE}/api/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ conversation_id: conversationId, question }),
    signal: controller.signal,
  }).then(async (response) => {
    const reader = response.body!.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop() || '';

      let currentEvent = '';
      for (const line of lines) {
        if (line.startsWith('event:')) {
          currentEvent = line.slice(6).trim();
        } else if (line.startsWith('data:')) {
          const dataStr = line.slice(5).trim();
          if (!dataStr) continue;
          try {
            const data = JSON.parse(dataStr);
            switch (currentEvent) {
              case 'conservative_start':
                callbacks.onConservativeStart();
                break;
              case 'conservative_token':
                callbacks.onConservativeToken(data.token);
                break;
              case 'conservative_end':
                callbacks.onConservativeEnd(data);
                break;
              case 'liberal_start':
                callbacks.onLiberalStart();
                break;
              case 'liberal_token':
                callbacks.onLiberalToken(data.token);
                break;
              case 'liberal_end':
                callbacks.onLiberalEnd(data);
                break;
              case 'consensus':
                callbacks.onConsensus(data);
                break;
            }
          } catch {
            // skip malformed JSON
          }
          currentEvent = '';
        }
      }
    }
  });

  return controller;
}
