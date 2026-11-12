import type { ReactNode } from "react";
import { strings } from "@/strings";

interface ExternalLinkProps {
  href: string;
  children: ReactNode;
  className?: string;
}

/** mame-curator-1138: a link that opens a new tab, and says so (WCAG G201).
    `rel` stops the new page reaching back into this one. */
export function ExternalLink({
  href,
  children,
  className = "underline",
}: ExternalLinkProps) {
  return (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      className={className}
    >
      {children}{" "}
      <span className="text-muted-foreground">
        {strings.common.opensInNewTab}
      </span>
    </a>
  );
}
