<script lang="ts">
  import { conversations, activeConversationId, refreshConversations } from '$lib/stores/conversations';
  import { deleteConversation } from '$lib/api';
  import type { Conversation } from '$lib/api';

  let { onSelectConversation, onNewChat }: {
    onSelectConversation: (id: string) => void;
    onNewChat: () => void;
  } = $props();

  let hoveredId = $state<string | null>(null);

  function groupByDate(convs: Conversation[]): Record<string, Conversation[]> {
    const now = new Date();
    const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    const yesterday = new Date(today.getTime() - 86400000);
    const sevenDaysAgo = new Date(today.getTime() - 7 * 86400000);
    const thirtyDaysAgo = new Date(today.getTime() - 30 * 86400000);

    const groups: Record<string, Conversation[]> = {};

    for (const c of convs) {
      const d = new Date(c.updated_at);
      let label: string;
      if (d >= today) {
        label = '오늘';
      } else if (d >= yesterday) {
        label = '어제';
      } else if (d >= sevenDaysAgo) {
        label = '지난 7일';
      } else if (d >= thirtyDaysAgo) {
        label = '지난 30일';
      } else {
        label = '이전';
      }
      if (!groups[label]) groups[label] = [];
      groups[label].push(c);
    }

    return groups;
  }

  async function handleDelete(e: Event, id: string) {
    e.stopPropagation();
    await deleteConversation(id);
    await refreshConversations();
  }

  const groupOrder = ['오늘', '어제', '지난 7일', '지난 30일', '이전'];
</script>

<aside class="sidebar">
  <button class="new-chat-btn" onclick={onNewChat}>+ 새 대화</button>

  <div class="conversation-list">
    {#each groupOrder as groupLabel}
      {#if groupByDate($conversations)[groupLabel]}
        <div class="group">
          <div class="group-label">{groupLabel}</div>
          {#each groupByDate($conversations)[groupLabel] as conv (conv.id)}
            <button
              class="conv-item"
              class:active={$activeConversationId === conv.id}
              onclick={() => onSelectConversation(conv.id)}
              onmouseenter={() => hoveredId = conv.id}
              onmouseleave={() => hoveredId = null}
            >
              <span class="conv-title">{conv.title || '새 대화'}</span>
              {#if hoveredId === conv.id}
                <button class="delete-btn" onclick={(e) => handleDelete(e, conv.id)}>
                  &times;
                </button>
              {/if}
            </button>
          {/each}
        </div>
      {/if}
    {/each}
  </div>
</aside>

<style>
  .sidebar {
    width: 260px;
    min-width: 260px;
    background: var(--sidebar-bg);
    border-right: 1px solid var(--border);
    display: flex;
    flex-direction: column;
    height: 100%;
    overflow-y: auto;
  }

  .new-chat-btn {
    margin: 16px;
    padding: 10px 16px;
    background: var(--accent);
    color: white;
    border-radius: 8px;
    font-weight: 600;
    font-size: 14px;
    text-align: center;
    transition: opacity 0.2s;
  }

  .new-chat-btn:hover {
    opacity: 0.9;
  }

  .conversation-list {
    flex: 1;
    overflow-y: auto;
    padding: 0 8px;
  }

  .group {
    margin-bottom: 8px;
  }

  .group-label {
    padding: 8px 12px 4px;
    font-size: 12px;
    font-weight: 600;
    color: var(--text-muted);
    text-transform: uppercase;
  }

  .conv-item {
    display: flex;
    align-items: center;
    justify-content: space-between;
    width: 100%;
    padding: 8px 12px;
    border-radius: 6px;
    text-align: left;
    font-size: 13px;
    transition: background 0.15s;
    position: relative;
  }

  .conv-item:hover {
    background: var(--hover);
  }

  .conv-item.active {
    background: var(--hover);
    font-weight: 500;
  }

  .conv-title {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    flex: 1;
  }

  .delete-btn {
    flex-shrink: 0;
    width: 20px;
    height: 20px;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: 4px;
    font-size: 16px;
    color: var(--text-muted);
    margin-left: 4px;
  }

  .delete-btn:hover {
    background: var(--danger);
    color: white;
  }
</style>
