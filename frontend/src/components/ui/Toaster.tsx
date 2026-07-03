import { useToastStore, type ToastKind } from '../../stores/toast'

const KIND_STYLES: Record<ToastKind, string> = {
  success: 'bg-emerald-600',
  error: 'bg-red-600',
  info: 'bg-blue-600',
  warning: 'bg-amber-600',
}

export function Toaster() {
  const toasts = useToastStore((s) => s.toasts)
  const dismiss = useToastStore((s) => s.dismiss)

  return (
    <div
      aria-live="polite"
      className="pointer-events-none fixed bottom-4 right-4 z-50 flex w-80 flex-col gap-2"
    >
      {toasts.map((t) => (
        <div
          key={t.id}
          role="status"
          className={`pointer-events-auto flex items-start justify-between gap-3 rounded-lg px-4 py-3 text-sm text-white shadow-lg ${KIND_STYLES[t.kind]}`}
        >
          <span>{t.message}</span>
          <button
            type="button"
            aria-label="Dismiss notification"
            className="shrink-0 font-bold opacity-70 hover:opacity-100"
            onClick={() => dismiss(t.id)}
          >
            ×
          </button>
        </div>
      ))}
    </div>
  )
}
