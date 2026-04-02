import { writable } from 'svelte/store';
import type { Conversation } from '$lib/api';
import { listConversations } from '$lib/api';

export const conversations = writable<Conversation[]>([]);
export const activeConversationId = writable<string | null>(null);

export async function refreshConversations() {
  const list = await listConversations();
  conversations.set(list);
}
