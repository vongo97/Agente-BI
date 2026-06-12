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

export interface ChatMessage {
    id?: number;
    role: MessageRole;
    content: string;
    fig?: unknown;
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
    content: string;
    round_number: number;
    created_at: string;
}

export interface UserConfig {
    gemini_key: string;
    mistral_key: string;
    gamma_key: string;
    preferred_provider: string;
}
