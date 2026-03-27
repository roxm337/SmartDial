export type Agent = {
  id: number;
  name: string | null;
  script: string;
  retell_agent_id: string;
  retell_llm_id: string | null;
  created_at: string;
};

export type Campaign = {
  id: number;
  agent_id: number;
  status: string;
  created_at: string;
  total_calls: number;
  completed_calls: number;
};

export type Call = {
  id: number;
  campaign_id: number;
  retell_call_id: string | null;
  phone: string;
  name: string | null;
  status: string;
  transcript: string | null;
  duration: number | null;
  recording_url: string | null;
  created_at: string;
  updated_at: string;
};

export type DashboardData = {
  agents: Agent[];
  campaigns: Campaign[];
  calls: Call[];
  issues: string[];
};

type AgentPayload = {
  name: string | null;
  script: string;
};

type CampaignPayload = {
  agent_id: number;
  leads: Array<{
    name: string | null;
    phone: string;
  }>;
};

const DEFAULT_API_BASE_URL = "http://127.0.0.1:8000";

function apiBaseUrl() {
  return process.env.NEXT_PUBLIC_API_BASE_URL || DEFAULT_API_BASE_URL;
}

function buildUrl(path: string) {
  return `${apiBaseUrl()}${path}`;
}

async function parseResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    let detail = `Request failed with status ${response.status}`;
    try {
      const data = (await response.json()) as { detail?: unknown };
      if (typeof data.detail === "string") {
        detail = data.detail;
      } else if (data.detail !== undefined) {
        detail = JSON.stringify(data.detail);
      }
    } catch {}
    throw new Error(detail);
  }

  return (await response.json()) as T;
}

async function fetchCollection<T>(path: string): Promise<T[]> {
  const response = await fetch(buildUrl(path), {
    cache: "no-store",
  });
  return parseResponse<T[]>(response);
}

export async function fetchDashboardData(): Promise<DashboardData> {
  const [agentsResult, campaignsResult, callsResult] = await Promise.allSettled([
    fetchCollection<Agent>("/agents"),
    fetchCollection<Campaign>("/campaigns"),
    fetchCollection<Call>("/calls"),
  ]);

  const issues: string[] = [];

  if (agentsResult.status === "rejected") {
    issues.push(
      `Could not load agents: ${
        agentsResult.reason instanceof Error ? agentsResult.reason.message : "Unknown error"
      }`,
    );
  }
  if (campaignsResult.status === "rejected") {
    issues.push(
      `Could not load campaigns: ${
        campaignsResult.reason instanceof Error
          ? campaignsResult.reason.message
          : "Unknown error"
      }`,
    );
  }
  if (callsResult.status === "rejected") {
    issues.push(
      `Could not load calls: ${
        callsResult.reason instanceof Error ? callsResult.reason.message : "Unknown error"
      }`,
    );
  }

  return {
    agents: agentsResult.status === "fulfilled" ? agentsResult.value : [],
    campaigns: campaignsResult.status === "fulfilled" ? campaignsResult.value : [],
    calls: callsResult.status === "fulfilled" ? callsResult.value : [],
    issues,
  };
}

export async function createAgent(payload: AgentPayload) {
  const response = await fetch(buildUrl("/agents"), {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  return parseResponse<Agent>(response);
}

export async function createCampaign(payload: CampaignPayload) {
  const response = await fetch(buildUrl("/campaigns"), {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  return parseResponse(response);
}
