import { beforeEach, describe, expect, it, vi } from "vitest";

const press: Record<string, () => void> = {};
const postEvent = vi.fn();
const close = Object.assign(vi.fn(), { isAvailable: () => true });

vi.mock("@tma.js/sdk-react", () => ({
  backButton: {
    onClick: (listener: () => void) => {
      press.back = listener;
      return () => {};
    },
  },
  settingsButton: { onClick: () => () => {} },
  hapticFeedback: {},
  initData: {},
  miniApp: { close },
  openLink: () => {},
  postEvent: (...args: unknown[]) => {
    postEvent(...args);
  },
  retrieveLaunchParams: () => {
    throw new Error("outside telegram");
  },
  retrieveRawInitData: () => undefined,
}));

const { bindBackButton } = await import("./telegram");

function visibility(): boolean[] {
  return postEvent.mock.calls.map(([, payload]) => (payload as { is_visible: boolean }).is_visible);
}

describe("bindBackButton", () => {
  beforeEach(() => postEvent.mockClear());

  it("shows the button for the first handler and hides it when the last one goes", () => {
    const outer = bindBackButton(() => {});
    const inner = bindBackButton(() => {});
    expect(visibility()).toEqual([true]);
    inner();
    expect(visibility()).toEqual([true]);
    outer();
    expect(visibility()).toEqual([true, false]);
  });

  it("calls the topmost handler and closes the mini app once none is left", () => {
    const calls: string[] = [];
    const outer = bindBackButton(() => calls.push("outer"));
    const inner = bindBackButton(() => calls.push("inner"));
    press.back();
    inner();
    press.back();
    outer();
    press.back();
    expect(calls).toEqual(["inner", "outer"]);
    expect(close).toHaveBeenCalledTimes(1);
  });
});
