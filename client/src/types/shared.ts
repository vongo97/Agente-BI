export type MessageRole = 'user' | 'assistant';

export interface Metric {
    label: string;
    value: string | number;
    description?: string;
    icon?: string;
}

export interface AutoDashItem {
    title: string;
    fig?: unknown;
    insight?: string;
    error?: string;
}

export type AuditSeverity = 'alta' | 'media' | 'baja' | 'info';
export type AuditDirection = 'positive' | 'negative' | 'neutral';

export interface AuditFact {
    id: string;
    title: string;
    value: number;
    display_value: string;
    unit: string;
    category: string;
    severity: AuditSeverity;
    direction: AuditDirection;
    definition: string;
    evidence: string;
    sample_size: number;
}

export interface AuditProfile {
    source_name: string;
    rows: number;
    columns: number;
    column_names: string[];
    orders: number | null;
    date_start: string | null;
    date_end: string | null;
    grain: string;
    roles: Record<string, string | null>;
    quality: string[];
}

export interface AuditDefinition {
    term: string;
    definition: string;
}

export interface AuditPayload {
    insights: AuditFact[];
    profile: AuditProfile;
    definitions: AuditDefinition[];
    methodology: string[];
    source_name: string | null;
    generated_at: string;
    narrative_mode?: 'deterministic' | 'llm';
}

export interface AuditResponse {
    chat_id: number;
    message_id: number;
    analysis: string;
    figure?: unknown;
    audit: AuditPayload;
}

export interface AnalyzeResponse {
    chat_id: number;
    message_id: number;
    analysis: string;
    figure?: unknown;
    code?: string | null;
    audit?: AuditPayload;
    narrative_mode?: 'deterministic' | 'llm';
}

export interface ChatMessage {
    id?: number;
    role: MessageRole;
    content: string;
    fig?: unknown;
    audit?: AuditPayload;
    dashboardData?: {
        charts: AutoDashItem[];
        metrics: Metric[];
    };
}

export interface DataSource {
    id?: number;
    filename: string;
    name?: string;
    columns: string[];
    type?: 'file' | 'sql' | 'gsheets';
    created_at?: string;
}

export interface ChatSession {
    id: number;
    title: string;
    created_at: string;
}

export interface DashboardItem {
    id: number;
    chat_title: string;
    content: string;
    fig?: unknown;
    pinned_at: string;
}

export interface Simulation {
    id: number;
    user_id: string;
    title: string;
    hypothesis: string;
    data_source_id?: number;
    result_report?: string;
    status: 'pending' | 'running' | 'completed' | 'error';
    provider: string;
    current_round: number;
    created_at: string;
}

export interface SimulationAgent {
    id: number;
    simulation_id: number;
    name: string;
    role: string;
    description: string;
    personality: string;
    stance?: string;
}

export interface SimulationMessage {
    id: number;
    agent_id?: number;
    agent_name?: string;
    agent_role?: string;
    agent_description?: string;
    agent_personality?: string;
    content: string;
    round_number: number;
    created_at: string;
}

export interface UserConfig {
    gemini_key: string;
    mistral_key: string;
    gamma_key: string;
    groq_key?: string;
    preferred_provider: string;
}
