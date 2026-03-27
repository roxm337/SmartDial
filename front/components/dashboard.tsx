"use client";

import type { FormEvent, ReactNode } from "react";
import { useEffect, useMemo, useState, useTransition } from "react";
import { useRouter } from "next/navigation";

import type { Agent, Call, Campaign, DashboardData } from "@/lib/api";
import { createAgent, createCampaign } from "@/lib/api";

type Notice = {
  kind: "success" | "error";
  message: string;
};

const leadTemplate = [
  "Jane Doe,+14155550101",
  "John Smith,+14155550102",
].join("\n");

function parseLeads(input: string) {
  return input
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean)
    .map((line) => {
      const parts = line
        .split(",")
        .map((part) => part.trim())
        .filter(Boolean);
      const phone = parts.at(-1);
      if (!phone) {
        return null;
      }
      const name = parts.slice(0, -1).join(", ") || null;
      return { name, phone };
    })
    .filter((lead): lead is { name: string | null; phone: string } => lead !== null);
}

function formatDate(value: string) {
  return new Intl.DateTimeFormat("en-US", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

function formatDuration(duration: number | null) {
  if (duration === null) {
    return "Pending";
  }
  if (duration < 60) {
    return `${duration}s`;
  }

  const minutes = Math.floor(duration / 60);
  const seconds = duration % 60;
  return `${minutes}m ${seconds}s`;
}

function statusTone(status: string) {
  const normalized = status.toLowerCase();
  if (["completed", "ended"].includes(normalized)) {
    return "bg-emerald-100 text-emerald-900";
  }
  if (["error", "failed", "not_connected", "canceled"].includes(normalized)) {
    return "bg-rose-100 text-rose-900";
  }
  return "bg-amber-100 text-amber-950";
}

function StatCard({
  label,
  value,
  detail,
}: {
  label: string;
  value: string;
  detail: string;
}) {
  return (
    <div className="rounded-[2rem] border border-[var(--border)] bg-[var(--surface-strong)] p-5 shadow-[var(--shadow)] backdrop-blur">
      <p className="text-xs uppercase tracking-[0.32em] text-[var(--muted)]">{label}</p>
      <p className="mt-3 text-4xl font-semibold tracking-[-0.04em] text-[var(--foreground)]">
        {value}
      </p>
      <p className="mt-2 text-sm text-[var(--muted)]">{detail}</p>
    </div>
  );
}

function EmptyState({ title, description }: { title: string; description: string }) {
  return (
    <div className="rounded-[1.75rem] border border-dashed border-[var(--border)] bg-white/50 px-5 py-8 text-sm text-[var(--muted)]">
      <p className="font-medium text-[var(--foreground)]">{title}</p>
      <p className="mt-2 leading-6">{description}</p>
    </div>
  );
}

function DataPanel<T>({
  eyebrow,
  title,
  items,
  emptyTitle,
  emptyDescription,
  renderItem,
}: {
  eyebrow: string;
  title: string;
  items: T[];
  emptyTitle: string;
  emptyDescription: string;
  renderItem: (item: T) => ReactNode;
}) {
  return (
    <section className="rounded-[2rem] border border-[var(--border)] bg-[var(--surface)] p-5 shadow-[var(--shadow)] backdrop-blur">
      <p className="text-xs uppercase tracking-[0.32em] text-[var(--muted)]">{eyebrow}</p>
      <h2 className="mt-3 text-2xl font-semibold tracking-[-0.04em] text-[var(--foreground)]">
        {title}
      </h2>
      <div className="mt-5 grid gap-4">
        {items.length ? (
          items.map(renderItem)
        ) : (
          <EmptyState title={emptyTitle} description={emptyDescription} />
        )}
      </div>
    </section>
  );
}

function AgentCard({ agent }: { agent: Agent }) {
  return (
    <article className="rounded-[1.6rem] border border-[var(--border)] bg-white/75 p-4">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h3 className="text-lg font-semibold text-[var(--foreground)]">
            {agent.name || `Agent #${agent.id}`}
          </h3>
          <p className="mt-1 font-mono text-xs text-[var(--muted)]">{agent.retell_agent_id}</p>
        </div>
        <span className="rounded-full bg-stone-100 px-3 py-1 text-xs text-stone-700">
          {formatDate(agent.created_at)}
        </span>
      </div>
      <p className="mt-4 line-clamp-4 text-sm leading-6 text-[var(--muted)]">{agent.script}</p>
    </article>
  );
}

function CampaignCard({ campaign }: { campaign: Campaign }) {
  return (
    <article className="rounded-[1.6rem] border border-[var(--border)] bg-white/75 p-4">
      <div className="flex items-center justify-between gap-3">
        <h3 className="text-lg font-semibold text-[var(--foreground)]">
          Campaign #{campaign.id}
        </h3>
        <span className={`rounded-full px-3 py-1 text-xs font-medium ${statusTone(campaign.status)}`}>
          {campaign.status}
        </span>
      </div>
      <div className="mt-4 grid grid-cols-2 gap-3 text-sm text-[var(--muted)]">
        <div>
          <p className="text-xs uppercase tracking-[0.28em]">Agent</p>
          <p className="mt-1 font-medium text-[var(--foreground)]">#{campaign.agent_id}</p>
        </div>
        <div>
          <p className="text-xs uppercase tracking-[0.28em]">Progress</p>
          <p className="mt-1 font-medium text-[var(--foreground)]">
            {campaign.completed_calls}/{campaign.total_calls}
          </p>
        </div>
      </div>
      <p className="mt-4 text-sm text-[var(--muted)]">{formatDate(campaign.created_at)}</p>
    </article>
  );
}

function CallCard({ call }: { call: Call }) {
  return (
    <article className="rounded-[1.6rem] border border-[var(--border)] bg-white/75 p-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h3 className="text-lg font-semibold text-[var(--foreground)]">
            {call.name || call.phone}
          </h3>
          <p className="mt-1 font-mono text-xs text-[var(--muted)]">{call.phone}</p>
        </div>
        <span className={`rounded-full px-3 py-1 text-xs font-medium ${statusTone(call.status)}`}>
          {call.status}
        </span>
      </div>
      <div className="mt-4 grid grid-cols-2 gap-3 text-sm text-[var(--muted)]">
        <div>
          <p className="text-xs uppercase tracking-[0.28em]">Campaign</p>
          <p className="mt-1 font-medium text-[var(--foreground)]">#{call.campaign_id}</p>
        </div>
        <div>
          <p className="text-xs uppercase tracking-[0.28em]">Duration</p>
          <p className="mt-1 font-medium text-[var(--foreground)]">
            {formatDuration(call.duration)}
          </p>
        </div>
      </div>
      <p className="mt-4 text-sm leading-6 text-[var(--muted)]">
        {call.transcript
          ? call.transcript
          : "Transcript will appear after Retell sends the webhook."}
      </p>
      {call.recording_url && (
        <a
          href={call.recording_url}
          target="_blank"
          rel="noreferrer"
          className="mt-4 inline-flex text-sm font-medium text-[var(--accent)] underline-offset-4 hover:underline"
        >
          Open recording
        </a>
      )}
    </article>
  );
}

export default function Dashboard({
  agents,
  campaigns,
  calls,
  issues,
}: DashboardData) {
  const router = useRouter();
  const [isRefreshing, startRefresh] = useTransition();
  const [agentName, setAgentName] = useState("");
  const [agentScript, setAgentScript] = useState("");
  const [selectedAgentId, setSelectedAgentId] = useState(
    agents[0] ? String(agents[0].id) : "",
  );
  const [leadsText, setLeadsText] = useState(leadTemplate);
  const [submittingAgent, setSubmittingAgent] = useState(false);
  const [submittingCampaign, setSubmittingCampaign] = useState(false);
  const [notice, setNotice] = useState<Notice | null>(null);

  useEffect(() => {
    if (!agents.length) {
      setSelectedAgentId("");
      return;
    }

    const stillExists = agents.some((agent) => String(agent.id) === selectedAgentId);
    if (!selectedAgentId || !stillExists) {
      setSelectedAgentId(String(agents[0].id));
    }
  }, [agents, selectedAgentId]);

  const stats = useMemo(() => {
    const completedCalls = calls.filter((call) =>
      ["ended", "completed"].includes(call.status.toLowerCase()),
    ).length;

    return [
      {
        label: "Agents",
        value: String(agents.length),
        detail: "Retell voice agents ready for campaigns",
      },
      {
        label: "Campaigns",
        value: String(campaigns.length),
        detail: "Outbound batches launched from the console",
      },
      {
        label: "Completed Calls",
        value: String(completedCalls),
        detail: `${calls.length} calls tracked in total`,
      },
    ];
  }, [agents.length, campaigns.length, calls]);

  async function handleCreateAgent(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setNotice(null);

    if (!agentScript.trim()) {
      setNotice({ kind: "error", message: "Script is required to create an agent." });
      return;
    }

    setSubmittingAgent(true);
    try {
      await createAgent({
        name: agentName.trim() || null,
        script: agentScript.trim(),
      });
      setAgentName("");
      setAgentScript("");
      setNotice({ kind: "success", message: "Agent created." });
      startRefresh(() => router.refresh());
    } catch (error) {
      setNotice({
        kind: "error",
        message: error instanceof Error ? error.message : "Could not create agent.",
      });
    } finally {
      setSubmittingAgent(false);
    }
  }

  async function handleCreateCampaign(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setNotice(null);

    if (!selectedAgentId) {
      setNotice({ kind: "error", message: "Create an agent before launching a campaign." });
      return;
    }

    const leads = parseLeads(leadsText);
    if (!leads.length) {
      setNotice({
        kind: "error",
        message: "Add at least one lead using the format: Name,+14155550101",
      });
      return;
    }

    setSubmittingCampaign(true);
    try {
      await createCampaign({
        agent_id: Number(selectedAgentId),
        leads,
      });
      setNotice({
        kind: "success",
        message: `Campaign launched for ${leads.length} lead${leads.length > 1 ? "s" : ""}.`,
      });
      startRefresh(() => router.refresh());
    } catch (error) {
      setNotice({
        kind: "error",
        message: error instanceof Error ? error.message : "Could not create campaign.",
      });
    } finally {
      setSubmittingCampaign(false);
    }
  }

  const alertPanels = notice || issues.length > 0 || isRefreshing;

  return (
    <main className="mx-auto flex min-h-screen w-full max-w-7xl flex-col px-4 py-6 sm:px-6 lg:px-8">
      <section className="relative overflow-hidden rounded-[2.5rem] border border-[var(--border)] bg-[var(--surface)] px-6 py-8 shadow-[var(--shadow)] backdrop-blur sm:px-8 lg:px-10">
        <div className="absolute inset-y-0 right-0 hidden w-1/3 bg-[radial-gradient(circle_at_top,rgba(20,83,45,0.14),transparent_58%)] lg:block" />
        <div className="relative grid gap-8 lg:grid-cols-[1.25fr_0.9fr]">
          <div>
            <p className="text-xs uppercase tracking-[0.4em] text-[var(--muted)]">
              ArteFact / AI Calling
            </p>
            <h1 className="mt-4 max-w-3xl text-4xl font-semibold tracking-[-0.06em] text-[var(--foreground)] sm:text-5xl">
              Launch outbound Retell campaigns without leaving the console.
            </h1>
            <p className="mt-5 max-w-2xl text-base leading-7 text-[var(--muted)] sm:text-lg">
              Create an agent from a raw script, paste a lead list, and watch calls,
              transcripts, and durations land in the dashboard.
            </p>
          </div>
          <div className="grid gap-4 sm:grid-cols-3 lg:grid-cols-1">
            {stats.map((stat) => (
              <StatCard key={stat.label} {...stat} />
            ))}
          </div>
        </div>
      </section>

      {alertPanels && (
        <section className="mt-6 grid gap-3">
          {notice && (
            <div
              className={`rounded-2xl border px-4 py-3 text-sm ${
                notice.kind === "success"
                  ? "border-emerald-200 bg-emerald-50 text-emerald-900"
                  : "border-rose-200 bg-rose-50 text-rose-900"
              }`}
            >
              {notice.message}
            </div>
          )}
          {isRefreshing && (
            <div className="rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-950">
              Refreshing dashboard data...
            </div>
          )}
          {issues.map((issue) => (
            <div
              key={issue}
              className="rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-950"
            >
              {issue}
            </div>
          ))}
        </section>
      )}

      <section className="mt-6 grid gap-6 lg:grid-cols-2">
        <form
          onSubmit={handleCreateAgent}
          className="rounded-[2rem] border border-[var(--border)] bg-[var(--surface)] p-6 shadow-[var(--shadow)] backdrop-blur"
        >
          <div className="flex items-start justify-between gap-4">
            <div>
              <p className="text-xs uppercase tracking-[0.32em] text-[var(--muted)]">
                Create Agent
              </p>
              <h2 className="mt-3 text-2xl font-semibold tracking-[-0.04em]">
                Turn a sales script into a Retell voice agent.
              </h2>
            </div>
            <span className="rounded-full bg-[var(--accent-soft)] px-3 py-1 text-xs font-medium text-[var(--accent)]">
              POST /agents
            </span>
          </div>

          <div className="mt-6 grid gap-4">
            <label className="grid gap-2 text-sm">
              <span className="font-medium text-[var(--foreground)]">Agent name</span>
              <input
                value={agentName}
                onChange={(event) => setAgentName(event.target.value)}
                placeholder="ArteFact SDR"
                className="rounded-2xl border border-[var(--border)] bg-white/80 px-4 py-3 outline-none transition focus:border-[var(--accent)]"
              />
            </label>
            <label className="grid gap-2 text-sm">
              <span className="font-medium text-[var(--foreground)]">Script</span>
              <textarea
                value={agentScript}
                onChange={(event) => setAgentScript(event.target.value)}
                placeholder="You are calling on behalf of ArteFact..."
                rows={9}
                className="rounded-[1.5rem] border border-[var(--border)] bg-white/80 px-4 py-3 outline-none transition focus:border-[var(--accent)]"
              />
            </label>
          </div>

          <button
            type="submit"
            disabled={submittingAgent}
            className="mt-6 inline-flex items-center justify-center rounded-full bg-[var(--foreground)] px-5 py-3 text-sm font-medium text-white transition hover:bg-[#3b3128] disabled:cursor-not-allowed disabled:opacity-60"
          >
            {submittingAgent ? "Creating..." : "Create agent"}
          </button>
        </form>

        <form
          onSubmit={handleCreateCampaign}
          className="rounded-[2rem] border border-[var(--border)] bg-[var(--surface)] p-6 shadow-[var(--shadow)] backdrop-blur"
        >
          <div className="flex items-start justify-between gap-4">
            <div>
              <p className="text-xs uppercase tracking-[0.32em] text-[var(--muted)]">
                Launch Campaign
              </p>
              <h2 className="mt-3 text-2xl font-semibold tracking-[-0.04em]">
                Paste leads and trigger outbound calls immediately.
              </h2>
            </div>
            <span className="rounded-full bg-[var(--accent-soft)] px-3 py-1 text-xs font-medium text-[var(--accent)]">
              POST /campaigns
            </span>
          </div>

          <div className="mt-6 grid gap-4">
            <label className="grid gap-2 text-sm">
              <span className="font-medium text-[var(--foreground)]">Agent</span>
              <select
                value={selectedAgentId}
                onChange={(event) => setSelectedAgentId(event.target.value)}
                className="rounded-2xl border border-[var(--border)] bg-white/80 px-4 py-3 outline-none transition focus:border-[var(--accent)]"
              >
                <option value="">Select an agent</option>
                {agents.map((agent) => (
                  <option key={agent.id} value={agent.id}>
                    {agent.name || `Agent #${agent.id}`}
                  </option>
                ))}
              </select>
            </label>
            <label className="grid gap-2 text-sm">
              <span className="font-medium text-[var(--foreground)]">Leads</span>
              <textarea
                value={leadsText}
                onChange={(event) => setLeadsText(event.target.value)}
                placeholder={leadTemplate}
                rows={9}
                className="rounded-[1.5rem] border border-[var(--border)] bg-white/80 px-4 py-3 font-mono text-sm outline-none transition focus:border-[var(--accent)]"
              />
            </label>
            <p className="text-sm leading-6 text-[var(--muted)]">
              One lead per line. Use <span className="font-mono">Name,+14155550101</span> or{" "}
              <span className="font-mono">+14155550101</span>.
            </p>
          </div>

          <button
            type="submit"
            disabled={submittingCampaign || !agents.length}
            className="mt-6 inline-flex items-center justify-center rounded-full bg-[var(--accent)] px-5 py-3 text-sm font-medium text-white transition hover:bg-[#0f3e22] disabled:cursor-not-allowed disabled:opacity-60"
          >
            {submittingCampaign ? "Launching..." : "Launch campaign"}
          </button>
        </form>
      </section>

      <section className="mt-6 grid gap-6 xl:grid-cols-[0.9fr_1fr_1.15fr]">
        <DataPanel
          eyebrow="Agents"
          title="Configured voices"
          items={agents}
          emptyTitle="No agents yet"
          emptyDescription="Create your first Retell agent from the form above."
          renderItem={(agent) => <AgentCard key={agent.id} agent={agent} />}
        />
        <DataPanel
          eyebrow="Campaigns"
          title="Outbound batches"
          items={campaigns}
          emptyTitle="No campaigns launched"
          emptyDescription="Launch a campaign after at least one agent exists."
          renderItem={(campaign) => <CampaignCard key={campaign.id} campaign={campaign} />}
        />
        <DataPanel
          eyebrow="Calls"
          title="Live call results"
          items={calls}
          emptyTitle="No calls logged"
          emptyDescription="Calls will appear here as soon as a campaign starts."
          renderItem={(call) => <CallCard key={call.id} call={call} />}
        />
      </section>
    </main>
  );
}
