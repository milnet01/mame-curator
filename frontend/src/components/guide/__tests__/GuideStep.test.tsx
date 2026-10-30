/**
 * mame-curator-1144 INV-2 — every step change moves focus to that step's
 * heading, on Next and on Back. A partially sighted user using a screen
 * magnifier or reader follows focus, so a change that leaves it behind
 * leaves them on the old screen.
 */
import { useState } from "react";
import { describe, expect, it } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { GuideAction } from "../GuideAction";
import { GuideStep } from "../GuideStep";

function TwoSteps() {
  const [step, setStep] = useState(1);
  return (
    <MemoryRouter>
      {step === 1 ? (
        <GuideStep stepNumber={1} heading="First question" exitLabel="Leave">
          <GuideAction onClick={() => setStep(2)}>Next</GuideAction>
        </GuideStep>
      ) : (
        <GuideStep
          stepNumber={2}
          stepCount={6}
          heading="Second question"
          exitLabel="Leave"
          onBack={() => setStep(1)}
        >
          <GuideAction onClick={() => setStep(3)}>Unused</GuideAction>
        </GuideStep>
      )}
    </MemoryRouter>
  );
}

const heading = (name: string) => screen.getByRole("heading", { name });

describe("GuideStep", () => {
  it("moves focus to the heading on the way forward and on Back", async () => {
    const user = userEvent.setup();
    render(<TwoSteps />);
    await waitFor(() => expect(heading("First question")).toHaveFocus());

    await user.click(screen.getByRole("button", { name: "Next" }));
    await waitFor(() => expect(heading("Second question")).toHaveFocus());

    await user.click(screen.getByRole("button", { name: "Back" }));
    await waitFor(() => expect(heading("First question")).toHaveFocus());
  });

  it("gives a changed heading a new focus event, so a screen reader hears it", async () => {
    const ui = (heading: string) => (
      <MemoryRouter>
        <GuideStep heading={heading}>body</GuideStep>
      </MemoryRouter>
    );
    const { rerender } = render(ui("Counting the games"));
    await waitFor(() => expect(heading("Counting the games")).toHaveFocus());
    const heard: (string | null)[] = [];
    document.addEventListener("focusin", (e) =>
      heard.push((e.target as HTMLElement).textContent),
    );

    rerender(ui("This finds 2 games"));

    await waitFor(() => expect(heard).toEqual(["This finds 2 games"]));
    expect(heading("This finds 2 games")).toHaveFocus();
  });

  it("shows the step as text, with no total until the total is known", () => {
    render(<TwoSteps />);
    expect(screen.getByText("Step 1")).toBeInTheDocument();
  });

  it("omits Back when no handler is given, and always offers the exit", () => {
    render(<TwoSteps />);
    expect(
      screen.queryByRole("button", { name: "Back" }),
    ).not.toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Leave" })).toHaveAttribute(
      "href",
      "/",
    );
  });

  it("gives every action a large label and at least a 3rem target", () => {
    render(<TwoSteps />);
    const action = screen.getByRole("button", { name: "Next" });
    expect(action.className).toContain("text-xl");
    expect(action.className).toContain("min-h-12");
  });
});
