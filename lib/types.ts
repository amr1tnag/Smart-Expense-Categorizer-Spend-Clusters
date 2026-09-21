export type Metrics = {
  transactions: number;
  total_spend: number;
  low_confidence: number;
};

export type CategoryTotal = {
  category: string;
  total: number;
};

export type ClusterSummary = {
  cluster: number;
  label: string;
  transactions: number;
  total_spend: number;
  avg_amount: number;
  weekend_share: number;
  recurring_share: number;
  top_category: string;
};

export type TransactionRow = {
  date: string;
  description: string;
  amount: number;
  abs_amount: number;
  category: string;
  confidence: number;
  cluster_label: string;
};

export type AnalyzeResponse = {
  metrics: Metrics;
  categories: CategoryTotal[];
  clusters: {
    silhouette: number | null;
    summary: ClusterSummary[];
  };
  rows: TransactionRow[];
};

export type AnalyzeError = {
  error: string;
};
