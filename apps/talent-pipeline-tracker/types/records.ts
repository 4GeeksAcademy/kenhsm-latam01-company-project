export type CandidateRecord = {
  id: string;
  full_name: string;
  email: string;
  position: string;
  status: string;
  stage: string;
};

export type CandidateRecordDetail = {
  id: string;
  full_name: string;
  email: string;
  phone: string;
  position: string;
  linkedin_url: string;
  cv_url: string;
  status: string;
  stage: string;
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
  status: string;
  stage: string;
  experience_years: number;
};

export type PatchResponse = {
  status: string;
  stage: string;
};