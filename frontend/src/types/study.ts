import type { Source } from './api';

export type StudyStep = 'diagnose' | 'explain' | 'practice' | 'review';
export type StudyAction = 'open' | 'view' | 'submit' | 'explain' | 'practice' | 'hint' | 'solution' | 'retry' | 'ai';
type StudyMistake = 'one_partition' | 'missing_partition' | 'only_endpoints' | 'missing_neighbors' | 'extra_values';

export interface StudyState {
  step: StudyStep;
  variant: 0 | 1 | 2;
  diagnosis: StudyMistake | 'correct' | null;
  practice_mistake: StudyMistake | null;
  hint_level: number;
  last_result: 'independent' | 'needs_practice' | null;
  last_mistake: StudyMistake | null;
  mistake_count: number;
}

export interface StudyTopic {
  id: string;
  title: string;
  goal: string;
  page: number;
}

export interface StudyCatalog {
  topics: StudyTopic[];
  ai_configured: boolean;
}

export interface SavedStudy {
  sessionId: string;
  state?: StudyState;
}

export interface StudyTurn {
  state: StudyState;
  session_id: string | null;
  revision: number | null;
  prompt: string | null;
  feedback: string | null;
  lesson: string | null;
  hint: string | null;
  sources: Source[];
  ai_status: 'used' | 'not_configured' | 'unavailable' | 'insufficient_evidence' | null;
  ai_message: string | null;
  ai_answer: string | null;
  ai_sources: Source[];
}
