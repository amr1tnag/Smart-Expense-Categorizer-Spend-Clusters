export type CategoryId =
  | "travel"
  | "food"
  | "shopping"
  | "bills"
  | "entertainment"
  | "health"
  | "rent"
  | "other";

export type Metrics = {
  transactions: number;
  total_spend: number;
  low_confidence: number;
  recurring_monthly: number;
  date_from: string | null;
  date_to: string | null;
};

export type CategoryTotal = {
  category: CategoryId;
  total: number;
  count: number;
  share: number;
};

export type MonthTotal = {
  month: string; // YYYY-MM
  total: number;
  by_category: Partial<Record<CategoryId, number>>;
};

export type RecurringPayment = {
  merchant: string;
  category: CategoryId | null;
  payments: number;
  typical_amount: number;
  cadence_days: number;
  monthly_equivalent: number;
  last_date: string;
};

export type ClusterSummary = {
  cluster: number;
  label: string;
  transactions: number;
  total_spend: number;
  avg_amount: number;
  weekend_share: number;
  recurring_share: number;
  top_category: CategoryId | "-";
  share: number;
};

export type TransactionRow = {
  date: string;
  description: string;
  amount: number;
  abs_amount: number;
  category: CategoryId;
  confidence: number;
  cluster_label: string;
  recurring: boolean;
  low_confidence: boolean;
  corrected: boolean;
};

export type AnalyzeResponse = {
  metrics: Metrics;
  categories: CategoryTotal[];
  monthly: MonthTotal[];
  recurring: RecurringPayment[];
  clusters: {
    silhouette: number | null;
    k: number;
    auto: boolean;
    summary: ClusterSummary[];
  };
  rows: TransactionRow[];
  corrections_applied: number;
  evaluation?: { accuracy: number; rows: number };
};

export type Corrections = Record<string, CategoryId>;
