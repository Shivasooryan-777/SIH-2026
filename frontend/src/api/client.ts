import type {
  Port,
  VesselType,
  Route,
  MarketWatchResponse,
  DecisionEvaluationRequest,
  DecisionEvaluationResponse,
  ActionResponse,
} from './types';

export const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

async function request<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const url = `${API_BASE_URL}${endpoint}`;
  const res = await fetch(url, {
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
    ...options,
  });

  if (!res.ok) {
    let errorDetail = `HTTP ${res.status}: ${res.statusText}`;
    try {
      const errJson = await res.json();
      if (errJson.detail) {
        errorDetail = typeof errJson.detail === 'string'
          ? errJson.detail
          : JSON.stringify(errJson.detail);
      }
    } catch {
      // ignore parse error
    }
    throw new Error(errorDetail);
  }

  return res.json();
}

export async function fetchHealth(): Promise<{ status: string; database: string }> {
  return request('/health');
}

export async function fetchPorts(): Promise<Port[]> {
  return request('/api/ports');
}

export async function fetchVesselTypes(): Promise<VesselType[]> {
  return request('/api/vessel-types');
}

export async function fetchRoutes(): Promise<Route[]> {
  return request('/api/routes');
}

export async function fetchMarketWatch(): Promise<MarketWatchResponse> {
  return request('/api/interaction/market-watch');
}

export async function evaluateDecision(
  payload: DecisionEvaluationRequest
): Promise<DecisionEvaluationResponse> {
  return request('/api/decision/evaluate', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export async function markDecisionActioned(
  decisionId: number,
  note?: string
): Promise<ActionResponse> {
  return request('/api/interaction/action', {
    method: 'POST',
    body: JSON.stringify({ decision_id: decisionId, note }),
  });
}
