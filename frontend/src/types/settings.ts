export interface SettingItem {
  key: string;
  label: string;
  value: string;
  is_secret: boolean;
}

export interface SettingHistoryItem {
  id: string;
  key: string;
  old_value: string | null;
  new_value: string | null;
  updated_at: string;
}
