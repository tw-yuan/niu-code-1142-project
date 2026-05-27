interface Props {
  selected: string[];
  onChange: (formats: string[]) => void;
}

const FORMATS = [
  { value: 'txt', label: '純文字', desc: '基礎文字輸出' },
  { value: 'docx', label: 'Word (.docx)', desc: '適合報告型作業' },
  { value: 'pdf', label: 'PDF', desc: '適合列印與提交' },
  { value: 'xlsx', label: 'Excel (.xlsx)', desc: '適合表格或資料分析型作業' },
];

export default function OutputFormatSelector({ selected, onChange }: Props) {
  const toggle = (val: string) => {
    if (selected.includes(val)) {
      onChange(selected.filter((v) => v !== val));
    } else {
      onChange([...selected, val]);
    }
  };

  return (
    <div>
      <label className="block text-sm font-medium text-gray-700 mb-2">輸出格式</label>
      <div className="grid grid-cols-2 gap-2">
        {FORMATS.map((f) => (
          <label
            key={f.value}
            className={`flex items-start gap-2 border rounded-lg p-3 cursor-pointer transition ${
              selected.includes(f.value)
                ? 'border-blue-400 bg-blue-50'
                : 'border-gray-200 hover:border-gray-300'
            }`}
          >
            <input
              type="checkbox"
              checked={selected.includes(f.value)}
              onChange={() => toggle(f.value)}
              className="mt-1"
            />
            <div>
              <p className="text-sm font-medium">{f.label}</p>
              <p className="text-xs text-gray-500">{f.desc}</p>
            </div>
          </label>
        ))}
      </div>
    </div>
  );
}
