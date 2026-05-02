import {
  CircleCheckIcon,
  InfoIcon,
  Loader2Icon,
  OctagonXIcon,
  TriangleAlertIcon,
} from "lucide-react"
import { Toaster as Sonner, type ToasterProps } from "sonner"

/**
 * Project-tweak vs vendored shadcn `sonner.tsx`: dropped the
 * `useTheme()` hook from `next-themes` (FP11 § B10 — the provider was
 * never mounted, so `theme` always defaulted to `'system'` and the
 * dep was dead weight). Caller passes the explicit `theme` prop now.
 */
const Toaster = ({ ...props }: ToasterProps) => {
  return (
    <Sonner
      theme={props.theme ?? "system"}
      className="toaster group"
      icons={{
        success: <CircleCheckIcon className="size-4" />,
        info: <InfoIcon className="size-4" />,
        warning: <TriangleAlertIcon className="size-4" />,
        error: <OctagonXIcon className="size-4" />,
        loading: <Loader2Icon className="size-4 animate-spin" />,
      }}
      style={
        {
          "--normal-bg": "var(--popover)",
          "--normal-text": "var(--popover-foreground)",
          "--normal-border": "var(--border)",
          "--border-radius": "var(--radius)",
        } as React.CSSProperties
      }
      {...props}
    />
  )
}

export { Toaster }
