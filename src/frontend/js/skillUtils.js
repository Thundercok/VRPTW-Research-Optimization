export const SKILL_CONFIG = {
  None: {
    color: 'var(--text-muted)',
    bg: 'transparent',
    border: 'var(--border-strong)',
    icon: `<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" style="margin-right: 4px; opacity: 0.6;"><circle cx="12" cy="12" r="10"></circle><line x1="4.93" y1="4.93" x2="19.07" y2="19.07"></line></svg>`
  },
  Refrigerated: {
    color: 'var(--blue)',
    bg: 'var(--blue-wash)',
    border: 'rgba(37,99,235,0.2)',
    icon: `<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" style="margin-right: 4px;"><line x1="12" y1="2" x2="12" y2="22"></line><line x1="12" y1="2" x2="16" y2="6"></line><line x1="12" y1="2" x2="8" y2="6"></line><line x1="12" y1="22" x2="16" y2="18"></line><line x1="12" y1="22" x2="8" y2="18"></line><line x1="2" y1="12" x2="22" y2="12"></line><line x1="2" y1="12" x2="6" y2="8"></line><line x1="2" y1="12" x2="6" y2="16"></line><line x1="22" y1="12" x2="18" y2="8"></line><line x1="22" y1="12" x2="18" y2="16"></line></svg>` // Basic snowflake-ish shape
  },
  Hazmat: {
    color: 'var(--danger)',
    bg: 'var(--alert-wash)',
    border: 'rgba(161,53,15,0.2)',
    icon: `<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" style="margin-right: 4px;"><path d="M8.5 14.5A2.5 2.5 0 0011 12c0-1.38-.5-2-1-3-1.072-2.143-.224-4.054 2-6 .5 2.5 2 4.9 4 6.5 2 1.6 3 3.5 3 5.5a7 7 0 11-14 0c0-1.153.433-2.294 1-3a2.5 2.5 0 002.5 2.5z"></path></svg>` // Flame icon
  },
  Express: {
    color: 'var(--purple)',
    bg: 'var(--purple-wash)',
    border: 'rgba(124,58,237,0.2)',
    icon: `<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" style="margin-right: 4px;"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"></polygon></svg>` // Zap icon
  }
};

export function createSkillBadge(skillName) {
  const normalized = skillName || 'None';
  const config = SKILL_CONFIG[normalized] || SKILL_CONFIG['None'];
  
  if (normalized === 'None') {
    return `<span style="color: ${config.color}; font-size: 10.5px; font-weight: 500; display: inline-flex; align-items: center;">${config.icon} None</span>`;
  }

  return `<span style="background: ${config.bg}; color: ${config.color}; border: 1px solid ${config.border}; font-weight: 600; padding: 2px 6px; border-radius: 4px; font-size: 10.5px; display: inline-flex; align-items: center; letter-spacing: -0.01em;">${config.icon}${normalized}</span>`;
}
