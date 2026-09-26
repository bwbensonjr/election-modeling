export type Incumbency = "No_Incumbent" | "Dem_Incumbent" | "GOP_Incumbent";

export interface Summary {
  point_margin: number;
  lower_90: number;
  upper_90: number;
  dem_win_probability: number;
}

export interface RaceInputs {
  PVI_N: number;
  incumbent_status: Incumbency;
  dem_receipts: number | null;
  opponent_receipts: number | null;
  money_predictor: string | null;
  money_logratio: number | null;
}

export interface SupportRow {
  target_id: string;
  component: string;
  predictor: string;
  target_value: string | number;
  training_min: number | null;
  training_max: number | null;
  training_races: number;
  training_election_dates: number;
  warning: string;
}

export interface CandidateMeta {
  name: string;
  party: "D" | "R";
  municipality: string;
  is_incumbent: boolean;
}

export interface RaceMeta {
  target_id: string;
  election_date: string;
  office: string;
  district: string;
  district_display: string;
  dem_candidate: CandidateMeta;
  comparison_candidate: CandidateMeta;
  component: string;
  asset: string;
  published: Summary;
  inputs: RaceInputs;
  support: SupportRow[];
}

export interface NumericSupport {
  minimum: number;
  maximum: number;
}

export interface ComponentMeta {
  asset: string;
  predictors: string[];
  scenario_terms: string[];
  numeric_support: Record<string, NumericSupport>;
  categorical_support: Record<string, Record<Incumbency, number>>;
}

export interface Manifest {
  schema_version: number;
  election: string;
  horizon: string;
  variant: string;
  variant_declaration: string;
  definition: string;
  training_cutoff: string;
  finance_cutoff: string;
  source_code_commit: string;
  source_snapshot: string;
  source_snapshot_url: string;
  source_digests: Record<string, string>;
  summary_tolerances: Record<keyof Summary, number>;
  draw_count: number;
  components: Record<string, ComponentMeta>;
  races: RaceMeta[];
  assets: Record<string, string>;
}

export interface RaceAsset {
  schema_version: number;
  target_id: string;
  draws: number[];
}

export interface ComponentAsset {
  schema_version: number;
  component: string;
  predictors: string[];
  terms: Record<string, number[]>;
  numeric_support: Record<string, NumericSupport>;
  categorical_support: Record<string, Record<Incumbency, number>>;
}

export interface ScenarioInputs {
  incumbent_status: Incumbency;
  dem_receipts: number | null;
  opponent_receipts: number | null;
}
