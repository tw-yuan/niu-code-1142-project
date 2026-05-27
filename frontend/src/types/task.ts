export interface TaskData {
  id: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  assignment_text: string;
  output_formats: string[];
  input_summary: string | null;
  output_text: string | null;
  structured_output_json: StructuredOutput | null;
  error_message: string | null;
  created_at: string;
  updated_at: string;
  uploaded_files: UploadedFileInfo[];
  generated_files: GeneratedFileInfo[];
  progress_events: ProgressEventInfo[];
}

export interface StructuredOutput {
  title: string;
  assignment_summary: string;
  requirements_breakdown: string[];
  answer_outline: string[];
  generated_draft: string;
  references: Reference[];
  limitations: string[];
  academic_integrity_notice: string;
  human_review_checklist: string[];
}

export interface Reference {
  source_name: string;
  quote_or_summary: string;
  used_for: string;
}

export interface UploadedFileInfo {
  id: string;
  filename: string;
  file_type: string;
  file_size: number;
  category: string;
  parse_status: string;
  parsed_text_preview: string | null;
  error_message: string | null;
}

export interface GeneratedFileInfo {
  id: string;
  format: string;
  status: string;
  error_message: string | null;
}

export interface ProgressEventInfo {
  id: string;
  event_type: string;
  message: string;
  detail: Record<string, unknown> | null;
  created_at: string;
}

export interface HistoryItem {
  id: string;
  assignment_text: string;
  status: string;
  input_summary: string | null;
  output_formats: string[];
  created_at: string;
  updated_at: string;
  has_output: boolean;
  file_count: number;
}
