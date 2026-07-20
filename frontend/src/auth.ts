export type Role = 'admin' | 'reviewer' | 'doctor';

export interface Session {
  token: string;
  username: string;
  role: Role;
}

const SESSION_KEY = 'med_ai_session';

function decodePayload(token: string): Record<string, unknown> | null {
  try {
    const payload = token.split('.')[1];
    if (!payload) return null;
    const json = atob(payload.replace(/-/g, '+').replace(/_/g, '/'));
    return JSON.parse(json);
  } catch {
    return null;
  }
}

export function getSession(): Session | null {
  const raw = localStorage.getItem(SESSION_KEY);
  if (!raw) return null;
  try {
    const stored = JSON.parse(raw) as Omit<Session, 'role'>;
    const payload = decodePayload(stored.token);
    const role = payload?.role;
    const username = payload?.sub;
    const expired = typeof payload?.exp === 'number' && payload.exp * 1000 <= Date.now();
    if (expired || typeof role !== 'string' || typeof username !== 'string' || !['admin', 'reviewer', 'doctor'].includes(role)) {
      clearSession();
      return null;
    }
    return { token: stored.token, username, role: role as Role };
  } catch {
    clearSession();
    return null;
  }
}

export function saveSession(token: string): Session | null {
  const payload = decodePayload(token);
  const role = payload?.role;
  const username = payload?.sub;
  if (typeof role !== 'string' || typeof username !== 'string' || !['admin', 'reviewer', 'doctor'].includes(role)) return null;
  const session: Session = { token, username, role: role as Role };
  localStorage.setItem(SESSION_KEY, JSON.stringify(session));
  return session;
}

export function clearSession() { localStorage.removeItem(SESSION_KEY); }
export const portalPath = (role: Role) => role === 'doctor' ? '/search' : '/dashboard';
