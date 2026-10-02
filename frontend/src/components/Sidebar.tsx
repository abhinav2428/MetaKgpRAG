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
const IconSignOut = () => (
  <svg width="15" height="15" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
    <path d="M9 21H5a2 2 0 01-2-2V5a2 2 0 012-2h4M16 17l5-5-5-5M21 12H9" strokeLinecap="round" strokeLinejoin="round"/>
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
          <div className="user-card">
            <div className="user-avatar">{initials}</div>
            <div className="user-info">
              <div className="user-name">{user.name || user.email}</div>
              <div className="user-sub">IIT Kharagpur</div>
            </div>
            <button className="user-settings" onClick={signout} title="Sign out">
              <IconSignOut />
            </button>
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
