import { useEffect, useRef, type ReactNode } from "react";
import { GuideAction } from "./GuideAction";
import { strings } from "@/strings";

interface GuideStepProps {
  heading: string;
  stepNumber?: number;
  /** Absent until the total is known, which is the first step. */
  stepCount?: number;
  /** Change it to move focus to the heading again, though its text is the same. */
  focusKey?: number;
  /** Absent where there is nothing to go back to. */
  onBack?: () => void;
  /** Absent where leaving would strand something, as a paused copy would be. */
  exitLabel?: string;
  children: ReactNode;
}

/**
 * One screen of a guide: one question, in large text, with one column of
 * large actions. Every step of this and later wizards renders through it.
 */
export function GuideStep({
  heading,
  stepNumber,
  stepCount,
  focusKey,
  onBack,
  exitLabel,
  children,
}: GuideStepProps) {
  const headingRef = useRef<HTMLHeadingElement>(null);

  // INV-2: focus follows the step, so a magnifier or screen reader does too.
  // The next frame, because the new step's content has to be on screen first.
  useEffect(() => {
    const id = requestAnimationFrame(() => headingRef.current?.focus());
    return () => cancelAnimationFrame(id);
  }, [heading, focusKey]);

  return (
    <div
      data-testid="guide-step"
      className="mx-auto flex w-full max-w-[40rem] flex-col gap-4 p-6"
    >
      {stepNumber !== undefined && (
        <p className="text-lg text-muted-foreground">
          {strings.guide.stepOf(stepNumber, stepCount)}
        </p>
      )}
      {/* A new element per text: focusing the one already focused fires
          nothing, so a screen reader would not hear the result. */}
      <h1
        key={heading}
        ref={headingRef}
        tabIndex={-1}
        className="text-3xl font-semibold focus:outline-none"
      >
        {heading}
      </h1>
      <div className="flex flex-col gap-3">{children}</div>
      <div className="mt-4 flex flex-col gap-3 border-t pt-4">
        {onBack && (
          <GuideAction onClick={onBack}>{strings.guide.back}</GuideAction>
        )}
        {exitLabel !== undefined && (
          <GuideAction to="/">{exitLabel}</GuideAction>
        )}
      </div>
    </div>
  );
}
