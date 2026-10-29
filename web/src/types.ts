export type Customer = {
  customer_id: string;
  industry: string;
  region: string;
  tenure_months: string;
  products: string;
  monthly_recurring_revenue: string;
  support_tier: string;
  churn_probability: string;
  offer_code?: string;
  offer?: string;
  reason?: string;
  message?: string;
  risk_weighted_mrr_index?: string;
};
export type Task = {
  task_id: string;
  status: string;
  total: number;
  succeeded: number;
  failed: number;
  error?: string | null;
  results?: Array<Record<string, string>>;
  offer_distribution?: Record<string, number>;
  risk_weighted_mrr_index?: number;
  risk_index_label?: string;
  synthetic_data?: boolean;
  human_approval_required?: boolean;
  failed_records?: Array<{
    row_number: string;
    customer_id: string;
    error: string;
  }>;
};
