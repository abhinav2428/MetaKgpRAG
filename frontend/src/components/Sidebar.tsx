import { useState, useCallback } from 'react';
import { useAuth } from '../contexts/AuthContext';
import type { Conversation } from '../api/client';

interface Props {
  conversations: Conversation[];
  activeId: string | null;
  onSelect: (id: string) => void;
  onNew: () => void;
  onDelete: (id: string) => void;
  onSignIn: () => void;
}

// Group conversations by time
function groupConversations(convs: Conversation[]) {
  const now = new Date();
  const today: Conversation[] = [];
  const week: Conversation[] = [];
  const older: Conversation[] = [];

  for (const c of convs) {
    const d = new Date(c.updated_at);
    const diffDays = (now.getTime() - d.getTime()) / (1000 * 60 * 60 * 24);
    if (diffDays < 1) today.push(c);
    else if (diffDays < 7) week.push(c);
    else older.push(c);
  }
  return { today, week, older };
}

// Icons
const IconMenu = () => (
  <svg width="16" height="16" fill="none" stroke="currentColor" strokeWidth="1.8" viewBox="0 0 24 24">
    <path d="M3 12h18M3 6h18M3 18h18" strokeLinecap="round"/>
  </svg>
);
const IconPlus = () => (
  <svg width="15" height="15" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
    <path d="M12 5v14M5 12h14" strokeLinecap="round"/>
  </svg>
);
const IconTrash = () => (
  <svg width="13" height="13" fill="none" stroke="currentColor" strokeWidth="1.8" viewBox="0 0 24 24">
    <path d="M3 6h18M8 6V4h8v2M19 6l-1 14H6L5 6" strokeLinecap="round" strokeLinejoin="round"/>
  </svg>
);
const IconSettings = () => (
  <svg width="14" height="14" fill="none" stroke="currentColor" strokeWidth="1.8" viewBox="0 0 24 24">
    <circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 00.33 1.82l.06.06a2 2 0 010 2.83 2 2 0 01-2.83 0l-.06-.06a1.65 1.65 0 00-1.82-.33 1.65 1.65 0 00-1 1.51V21a2 2 0 01-4 0v-.09A1.65 1.65 0 009 19.4a1.65 1.65 0 00-1.82.33l-.06.06a2 2 0 01-2.83-2.83l.06-.06A1.65 1.65 0 004.68 15a1.65 1.65 0 00-1.51-1H3a2 2 0 010-4h.09A1.65 1.65 0 004.6 9a1.65 1.65 0 00-.33-1.82l-.06-.06a2 2 0 012.83-2.83l.06.06A1.65 1.65 0 009 4.68a1.65 1.65 0 001-1.51V3a2 2 0 014 0v.09a1.65 1.65 0 001 1.51 1.65 1.65 0 001.82-.33l.06-.06a2 2 0 012.83 2.83l-.06.06A1.65 1.65 0 0019.4 9a1.65 1.65 0 001.51 1H21a2 2 0 010 4h-.09a1.65 1.65 0 00-1.51 1z"/>
  </svg>
);

function ConvGroup({ label, items, activeId, onSelect, onDelete, collapsed }: {
  label: string; items: Conversation[]; activeId: string | null;
  onSelect: (id: string) => void; onDelete: (id: string) => void; collapsed: boolean;
}) {
  if (items.length === 0) return null;
  return (
    <>
      {!collapsed && <div className="conv-group-label">{label}</div>}
      {items.map(c => (
        <div
          key={c.id}
          className={`conv-item ${c.id === activeId ? 'active' : ''}`}
          onClick={() => onSelect(c.id)}
          title={collapsed ? c.title : undefined}
        >
          <div className="conv-item-dot" />
          <span className="conv-item-title">{c.title}</span>
          <button
            className="conv-item-delete"
            onClick={(e) => { e.stopPropagation(); onDelete(c.id); }}
          >
            <IconTrash />
          </button>
        </div>
      ))}
    </>
  );
}

export default function Sidebar({ conversations, activeId, onSelect, onNew, onDelete, onSignIn }: Props) {
  const { user, signout } = useAuth();
  const [collapsed, setCollapsed] = useState(false);
  const { today, week, older } = groupConversations(conversations);

  const initials = user?.name
    ? user.name.split(' ').map(n => n[0]).join('').slice(0, 2).toUpperCase()
    : user?.email?.[0].toUpperCase() ?? 'G';

  return (
    <nav className={`sidebar ${collapsed ? 'collapsed' : ''}`}>
      {/* Header */}
      <div className="sidebar-header">
        <div className="sidebar-logo">
          <div className="sidebar-logo-icon">G</div>
          <span className="sidebar-logo-text">GraphMind</span>
        </div>
        <button className="collapse-btn" onClick={() => setCollapsed(c => !c)}>
          <IconMenu />
        </button>
      </div>

      {/* New chat */}
      <button className="new-chat-btn" onClick={onNew}>
        <IconPlus />
        <span className="btn-text">New chat</span>
      </button>

      {/* Conversations */}
      <div className="conversations-list">
        <ConvGroup label="Today"         items={today}  activeId={activeId} onSelect={onSelect} onDelete={onDelete} collapsed={collapsed} />
        <ConvGroup label="Previous 7 days" items={week} activeId={activeId} onSelect={onSelect} onDelete={onDelete} collapsed={collapsed} />
        <ConvGroup label="Older"         items={older}  activeId={activeId} onSelect={onSelect} onDelete={onDelete} collapsed={collapsed} />
      </div>

      {/* Footer */}
      <div className="sidebar-footer">
        {user ? (
          <div className="user-card" onClick={signout} title="Sign out">
            <div className="user-avatar">{initials}</div>
            <div className="user-info">
              <div className="user-name">{user.name || user.email}</div>
              <div className="user-sub">IIT Kharagpur</div>
            </div>
            <button className="user-settings"><IconSettings /></button>
          </div>
        ) : (
          <div className="auth-prompt">
            <p>Sign in to save your conversations</p>
            <button className="auth-prompt-btn primary" onClick={onSignIn}>Sign In</button>
            <button className="auth-prompt-btn ghost" onClick={onSignIn}>Create Account</button>
          </div>
        )}
      </div>
    </nav>
  );
}
