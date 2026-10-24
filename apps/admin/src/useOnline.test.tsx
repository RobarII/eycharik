import { act, render, renderHook, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { UpdateBanner } from "./components/UpdateBanner";
import { useOnline } from "./useOnline";

describe("UpdateBanner", () => {
  it("stays out of the way when the build is current and the network is up", () => {
    const { container } = render(<UpdateBanner offline={false} stale={false} onReload={vi.fn()} />);

    expect(container).toBeEmptyDOMElement();
  });

  it("offers a reload when a newer build landed", async () => {
    const onReload = vi.fn();
    render(<UpdateBanner offline={false} stale onReload={onReload} />);

    await userEvent.click(screen.getByRole("button", { name: "Перезагрузить" }));

    expect(onReload).toHaveBeenCalled();
  });

  it("does not ask for a reload when the network is gone", () => {
    render(<UpdateBanner offline stale onReload={vi.fn()} />);

    expect(screen.queryByRole("button", { name: "Перезагрузить" })).not.toBeInTheDocument();
    expect(screen.getByRole("status")).toHaveTextContent("Нет сети");
  });
});

describe("useOnline", () => {
  it("follows the browser's network events", () => {
    const { result } = renderHook(() => useOnline());

    expect(result.current).toBe(true);

    act(() => {
      window.dispatchEvent(new Event("offline"));
    });
    expect(result.current).toBe(false);

    act(() => {
      window.dispatchEvent(new Event("online"));
    });
    expect(result.current).toBe(true);
  });
});
