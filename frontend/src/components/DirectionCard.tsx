import type { Direction } from "../api/documents";

interface Props {
  direction: Direction;
  onClick: () => void;
}

export default function DirectionCard({ direction, onClick }: Props) {
  return (
    <button
      onClick={onClick}
      className="text-left p-4 rounded-xl border border-gray-200 bg-white hover:border-indigo-400 hover:shadow-md transition-all group relative"
    >
      {direction.is_dynamic && (
        <span className="absolute top-2 right-2 text-xs bg-indigo-50 text-indigo-500 px-1.5 py-0.5 rounded-full">
          ✨ 推薦
        </span>
      )}
      <div className="text-2xl mb-2">{direction.emoji}</div>
      <div className="font-semibold text-gray-800 group-hover:text-indigo-700 mb-1">
        {direction.label}
      </div>
      <div className="text-sm text-gray-500 leading-relaxed">{direction.description}</div>
    </button>
  );
}
