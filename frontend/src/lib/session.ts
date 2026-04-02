import { browser } from '$app/environment';

const SESSION_KEY = 'election_session_id';

function generateId(): string {
  return crypto.randomUUID();
}

export function getSessionId(): string {
  if (!browser) return '';
  let id = localStorage.getItem(SESSION_KEY);
  if (!id) {
    id = generateId();
    localStorage.setItem(SESSION_KEY, id);
  }
  return id;
}
