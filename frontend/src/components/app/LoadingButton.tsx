import { Loader2 } from "lucide-react"
import { ButtonHTMLAttributes, ReactNode } from "react"

interface Props extends ButtonHTMLAttributes<HTMLButtonElement> {
  loading?: boolean
  loadingText?: string
  icon?: ReactNode
  children: ReactNode
}

export function LoadingButton({
  loading = false,
  loadingText,
  icon,
  children,
  disabled,
  className = "",
  ...props
}: Props) {
  return (
    <button
      {...props}
      disabled={disabled || loading}
      aria-busy={loading}
      className={className}
    >
      {loading ? <Loader2 size={16} className="animate-spin" /> : icon}
      <span>{loading ? loadingText ?? children : children}</span>
    </button>
  )
}
