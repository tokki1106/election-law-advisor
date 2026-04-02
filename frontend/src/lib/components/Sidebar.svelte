<script lang="ts">
  import { conversations, activeConversationId, refreshConversations } from '$lib/stores/conversations';
  import { deleteConversation, updateConversation } from '$lib/api';
  import type { Conversation } from '$lib/api';

  let { onSelectConversation, onNewChat }: {
    onSelectConversation: (id: string) => void;
    onNewChat: () => void;
  } = $props();

  let hoveredId = $state<string | null>(null);
  let menuOpenId = $state<string | null>(null);
  let collapsedFolders = $state<Set<string>>(new Set());
  let renamingFolder = $state<string | null>(null);
  let newFolderName = $state('');

  // Group conversations: pinned first, then by folder, then by date
  interface SidebarGroup {
    label: string;
    type: 'pinned' | 'folder' | 'date';
    convs: Conversation[];
    collapsible: boolean;
  }

  function buildGroups(convs: Conversation[]): SidebarGroup[] {
    const groups: SidebarGroup[] = [];

    // 1. Pinned
    const pinned = convs.filter(c => c.pinned);
    if (pinned.length > 0) {
      groups.push({ label: '📌 고정됨', type: 'pinned', convs: pinned, collapsible: false });
    }

    // 2. Folders
    const folders = new Map<string, Conversation[]>();
    const ungrouped: Conversation[] = [];
    for (const c of convs.filter(c => !c.pinned)) {
      if (c.folder) {
        if (!folders.has(c.folder)) folders.set(c.folder, []);
        folders.get(c.folder)!.push(c);
      } else {
        ungrouped.push(c);
      }
    }

    for (const [folder, fConvs] of folders) {
      groups.push({ label: `📁 ${folder}`, type: 'folder', convs: fConvs, collapsible: true });
    }

    // 3. Date groups for ungrouped
    const now = new Date();
    const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    const yesterday = new Date(today.getTime() - 86400000);
    const sevenDaysAgo = new Date(today.getTime() - 7 * 86400000);

    const dateGroups: Record<string, Conversation[]> = {};
    for (const c of ungrouped) {
      const d = new Date(c.updated_at);
      let label: string;
      if (d >= today) label = '오늘';
      else if (d >= yesterday) label = '어제';
      else if (d >= sevenDaysAgo) label = '지난 7일';
      else label = '이전';
      if (!dateGroups[label]) dateGroups[label] = [];
      dateGroups[label].push(c);
    }

    for (const label of ['오늘', '어제', '지난 7일', '이전']) {
      if (dateGroups[label]) {
        groups.push({ label, type: 'date', convs: dateGroups[label], collapsible: true });
      }
    }

    return groups;
  }

  function toggleFolder(label: string) {
    const next = new Set(collapsedFolders);
    if (next.has(label)) next.delete(label);
    else next.add(label);
    collapsedFolders = next;
  }

  async function handleDelete(e: Event, id: string) {
    e.stopPropagation();
    menuOpenId = null;
    await deleteConversation(id);
    await refreshConversations();
  }

  async function handlePin(e: Event, conv: Conversation) {
    e.stopPropagation();
    menuOpenId = null;
    await updateConversation(conv.id, { pinned: !conv.pinned });
    await refreshConversations();
  }

  async function handleMoveToFolder(e: Event, convId: string, folder: string) {
    e.stopPropagation();
    menuOpenId = null;
    await updateConversation(convId, { folder });
    await refreshConversations();
  }

  async function handleRemoveFromFolder(e: Event, convId: string) {
    e.stopPropagation();
    menuOpenId = null;
    await updateConversation(convId, { folder: '' });
    await refreshConversations();
  }

  function toggleMenu(e: Event, id: string) {
    e.stopPropagation();
    menuOpenId = menuOpenId === id ? null : id;
  }

  function getExistingFolders(convs: Conversation[]): string[] {
    const set = new Set<string>();
    for (const c of convs) {
      if (c.folder) set.add(c.folder);
    }
    return [...set].sort();
  }

  function handleNewFolder(e: Event, convId: string) {
    e.stopPropagation();
    const name = prompt('폴더 이름을 입력하세요');
    if (name && name.trim()) {
      menuOpenId = null;
      updateConversation(convId, { folder: name.trim() }).then(() => refreshConversations());
    }
  }

  $effect(() => {
    // Close menu on outside click
    function handleClick() { menuOpenId = null; }
    document.addEventListener('click', handleClick);
    return () => document.removeEventListener('click', handleClick);
  });

  const sidebarGroups = $derived(buildGroups($conversations));
  const existingFolders = $derived(getExistingFolders($conversations));
</script>

<aside class="sidebar">
  <button class="new-chat-btn" onclick={onNewChat}>+ 새 대화</button>

  <div class="conversation-list">
    {#each sidebarGroups as group}
      <div class="group">
        <button
          class="group-label"
          class:collapsible={group.collapsible}
          onclick={() => group.collapsible && toggleFolder(group.label)}
        >
          {#if group.collapsible}
            <span class="chevron" class:collapsed={collapsedFolders.has(group.label)}>▾</span>
          {/if}
          {group.label}
          <span class="count">{group.convs.length}</span>
        </button>

        {#if !collapsedFolders.has(group.label)}
          {#each group.convs as conv (conv.id)}
            <div class="conv-item-wrapper">
              <button
                class="conv-item"
                class:active={$activeConversationId === conv.id}
                onclick={() => onSelectConversation(conv.id)}
                onmouseenter={() => hoveredId = conv.id}
                onmouseleave={() => { hoveredId = null; }}
              >
                <span class="conv-title">
                  {#if conv.pinned && group.type !== 'pinned'}📌{/if}
                  {conv.title || '새 대화'}
                </span>
                {#if hoveredId === conv.id}
                  <button class="menu-btn" onclick={(e) => toggleMenu(e, conv.id)}>⋯</button>
                {/if}
              </button>

              {#if menuOpenId === conv.id}
                <div class="context-menu" onclick={(e) => e.stopPropagation()}>
                  <button class="menu-item" onclick={(e) => handlePin(e, conv)}>
                    {conv.pinned ? '📌 고정 해제' : '📌 상단 고정'}
                  </button>
                  {#if conv.folder}
                    <button class="menu-item" onclick={(e) => handleRemoveFromFolder(e, conv.id)}>
                      📂 폴더에서 꺼내기
                    </button>
                  {/if}
                  {#each existingFolders.filter(f => f !== conv.folder) as folder}
                    <button class="menu-item" onclick={(e) => handleMoveToFolder(e, conv.id, folder)}>
                      📁 {folder}(으)로 이동
                    </button>
                  {/each}
                  <button class="menu-item" onclick={(e) => handleNewFolder(e, conv.id)}>
                    📁 새 폴더로 이동
                  </button>
                  <div class="menu-divider"></div>
                  <button class="menu-item danger" onclick={(e) => handleDelete(e, conv.id)}>
                    🗑 삭제
                  </button>
                </div>
              {/if}
            </div>
          {/each}
        {/if}
      </div>
    {/each}
  </div>
</aside>

<style>
  .sidebar {
    width: 280px;
    min-width: 280px;
    background: var(--sidebar-bg);
    border-right: 1px solid var(--border);
    display: flex;
    flex-direction: column;
    height: 100%;
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
    padding: 0 8px 16px;
  }

  .group {
    margin-bottom: 4px;
  }

  .group-label {
    display: flex;
    align-items: center;
    gap: 4px;
    padding: 8px 12px 4px;
    font-size: 12px;
    font-weight: 600;
    color: var(--text-muted);
    width: 100%;
    text-align: left;
  }

  .group-label.collapsible {
    cursor: pointer;
    border-radius: 4px;
  }

  .group-label.collapsible:hover {
    background: rgba(0,0,0,0.03);
  }

  .chevron {
    font-size: 10px;
    transition: transform 0.15s;
    display: inline-block;
  }

  .chevron.collapsed {
    transform: rotate(-90deg);
  }

  .count {
    margin-left: auto;
    font-size: 11px;
    color: var(--text-muted);
    opacity: 0.6;
  }

  .conv-item-wrapper {
    position: relative;
  }

  .conv-item {
    display: flex;
    align-items: center;
    justify-content: space-between;
    width: 100%;
    padding: 7px 12px;
    border-radius: 6px;
    text-align: left;
    font-size: 13px;
    transition: background 0.12s;
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

  .menu-btn {
    flex-shrink: 0;
    width: 24px;
    height: 24px;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: 4px;
    font-size: 14px;
    color: var(--text-muted);
    letter-spacing: 1px;
  }

  .menu-btn:hover {
    background: rgba(0,0,0,0.08);
  }

  .context-menu {
    position: absolute;
    left: 12px;
    top: 100%;
    z-index: 100;
    background: white;
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 4px 0;
    min-width: 180px;
    box-shadow: 0 4px 16px rgba(0,0,0,0.1);
  }

  .menu-item {
    display: block;
    width: 100%;
    padding: 7px 14px;
    text-align: left;
    font-size: 13px;
    transition: background 0.1s;
  }

  .menu-item:hover {
    background: var(--hover);
  }

  .menu-item.danger {
    color: var(--danger);
  }

  .menu-divider {
    height: 1px;
    background: var(--border);
    margin: 4px 0;
  }
</style>
