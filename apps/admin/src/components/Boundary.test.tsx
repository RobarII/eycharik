import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { Boundary } from "./Boundary";

let broken = false;

function Screen() {
  if (broken) throw new Error("step_title is not a string");
  return <p>Экран жив</p>;
}

describe("Boundary", () => {
  beforeEach(() => {
    broken = false;
    vi.spyOn(console, "error").mockImplementation(() => undefined);
  });

  it("keeps the shell instead of a blank page and names the error", () => {
    broken = true;

    render(
      <Boundary>
        <Screen />
      </Boundary>,
    );

    expect(screen.getByRole("alert")).toBeInTheDocument();
    expect(screen.getByText("step_title is not a string")).toBeInTheDocument();
  });

  it("renders the screen again once the crash is behind it", async () => {
    broken = true;
    render(
      <Boundary>
        <Screen />
      </Boundary>,
    );

    broken = false;
    await userEvent.click(screen.getByRole("button", { name: "Попробовать снова" }));

    expect(await screen.findByText("Экран жив")).toBeInTheDocument();
  });
});
