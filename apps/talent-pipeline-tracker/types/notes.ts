export type CandidateNote = {
  id: string;
  record_id: string;
  content: string;
  created_at: string;
};

export type NotesResponse = {
  data: CandidateNote[];
  meta?: {
    total?: number;
  };
};