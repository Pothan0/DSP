/**
 * API Service Layer — NovaSentinel Gateway
 *
 * Uses relative URLs so Vite's dev proxy forwards them to FastAPI on :8000.
 * In production, configure your reverse proxy (nginx) similarly.
 */

async function apiGet(path) {
  try {
    const res = await fetch(path);
    if (!res.ok) {
      const text = await res.text();
      throw new Error(`HTTP ${res.status}: ${text}`);
    }
    return await res.json();
  } catch (e) {
    console.error(`API GET ${path}:`, e.message);
    return null;
  }
}

async function apiPost(path, body) {
  try {
    const res = await fetch(path, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    if (!res.ok) {
      const text = await res.text();
      throw new Error(`HTTP ${res.status}: ${text}`);
    }
    return await res.json();
  } catch (e) {
    console.error(`API POST ${path}:`, e.message);
    return null;
  }
}

// ─── Health ─────────────────────────────────────────────────────────────────

export async function checkHealth() {
  return apiGet('/health');
}

// ─── Chat ───────────────────────────────────────────────────────────────────

/**
 * Send a message through the full 4-layer security pipeline.
 *
 * Backend expects:  { query: string, user_context: { user_id, name, role } }
 * Backend returns:  { safe_response, input_threat_assessment, pii_scrubbed_input,
 *                     pii_scrubbed_output, blocked, block_reason }
 */
export async function sendChat(query, userContext) {
  return apiPost('/api/v1/chat', { query, user_context: userContext });
}

// ─── Analytics ──────────────────────────────────────────────────────────────

/**
 * Returns: {
 *   event_counts:  { THREAT_BLOCKED: n, AGENT_INTERACTION: n },
 *   threat_history: [{ time, score }],
 *   pii_detected_sessions: n,
 *   pii_counts: { SSN: n, ... }
 * }
 */
export async function getAnalytics() {
  return apiGet('/api/v1/analytics');
}

// ─── Audit Logs ─────────────────────────────────────────────────────────────

/**
 * Returns array of: { id, timestamp, event_type, details, hash }
 */
export async function getLogs(limit = 50) {
  return apiGet(`/api/v1/logs?limit=${limit}`);
}

/**
 * Returns: { chain_valid: boolean }
 */
export async function verifyChain() {
  return apiGet('/api/v1/logs/verify');
}

// ─── Red Team ───────────────────────────────────────────────────────────────

/**
 * Test a single prompt against the ML threat scorer.
 *
 * Backend expects:  { query: string }
 * Backend returns:  { threat_score, is_malicious, semantic_score,
 *                     pattern_detected, category, patterns: [],
 *                     detected_categories: {} }
 */
export async function redTeamTest(query) {
  return apiPost('/api/v1/tools/red_team', { query });
}

/**
 * Test a single prompt through the FULL 4-layer security pipeline.
 *
 * Backend expects:  { query: string, user_context?: {...} }
 * Backend returns:  { query, layers: {}, final_verdict, blocked_at_layer, response_text }
 */
export async function redTeamTestFull(query, userContext) {
  return apiPost('/api/v1/tools/red_team_full', { query, user_context: userContext });
}
