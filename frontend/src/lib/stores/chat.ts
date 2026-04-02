import { writable } from 'svelte/store';

export interface ChatTurn {
  question: string;
  conservative: string;
  conservativeCited: string[];
  liberal: string;
  liberalCited: string[];
  consensus: string;
  consensusCited: string[];
  riskLevel: string;
  requestFeedback: boolean;
  feedbackGiven: 'up' | 'down' | null;
}

export const chatHistory = writable<ChatTurn[]>([]);
export const currentTurn = writable<ChatTurn | null>(null);
export const isStreaming = writable(false);
export const conservativeActive = writable(false);
export const liberalActive = writable(false);
export const conversationMode = writable<string | null>(null);

export function resetChat() {
  chatHistory.set([]);
  currentTurn.set(null);
  isStreaming.set(false);
  conservativeActive.set(false);
  liberalActive.set(false);
  conversationMode.set(null);
}
