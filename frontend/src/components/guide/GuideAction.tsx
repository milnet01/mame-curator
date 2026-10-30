import type { ReactNode } from "react";
import { Link } from "react-router";
import { cn } from "@/lib/utils";

interface GuideActionProps {
  children: ReactNode;
  /** A button when given onClick, a link when given to. */
  onClick?: () => void;
  to?: string;
  disabled?: boolean;
  /** The step's main action, drawn filled. */
  primary?: boolean;
}

/** The large action every guide step uses, here and in later wizards. */
export function GuideAction({
  children,
  onClick,
  to,
  disabled,
  primary,
}: GuideActionProps) {
  const className = cn(
    "flex min-h-12 w-full items-center rounded-md border px-4 py-2 text-left text-xl",
    "focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-ring",
    "disabled:cursor-not-allowed disabled:opacity-50",
    primary
      ? "border-primary bg-primary text-primary-foreground hover:bg-primary/90"
      : "bg-background hover:bg-muted",
  );
  if (to !== undefined) {
    return (
      <Link to={to} className={className}>
        {children}
      </Link>
    );
  }
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      className={className}
    >
      {children}
    </button>
  );
}
