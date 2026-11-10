export type CandidateStatus = "received" | "in_progress" | "selected" | "discarded";

export type CandidateStage =
  | "pending"
  | "review"
  | "personal_interview"
  | "technical_interview"
  | "offer_presented";

export type CandidateRecord = {
  id: string;
  full_name: string;
  email: string;
  position: string;
  status: CandidateStatus;
  stage: CandidateStage;
};

export type CandidateRecordDetail = {
  id: string;
  full_name: string;
  email: string;
  phone: string;
  position: string;
  linkedin_url: string;
  cv_url: string;
  status: CandidateStatus;
  stage: CandidateStage;
  experience_years: number;
  notes_count: number;
  applied_at: string;
  updated_at: string;
};

export type RecordsResponse = {
  total: number;
  page: number;
  limit: number;
  data: CandidateRecord[];
};

export type CandidatePayload = {
  full_name: string;
  email: string;
  phone: string;
  position: string;
  linkedin_url: string;
  cv_url: string;
  status: CandidateStatus;
  stage: CandidateStage;
  experience_years: number;
};

export type PatchResponse = {
  status: CandidateStatus;
  stage: CandidateStage;
};