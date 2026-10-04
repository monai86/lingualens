import "@testing-library/jest-dom/vitest";
import { render, type RenderResult } from "@testing-library/react";
import { beforeEach, vi } from "vitest";

import { resetApiRuntimeSettingsCacheForTests } from "@/lib/api";

export const routerPush = vi.fn();
export const routerReplace = vi.fn();
export const routerRefresh = vi.fn();
export const redirectMock = vi.fn((href: string): never => {
  const error = new Error("NEXT_REDIRECT");
  Object.assign(error, { digest: `NEXT_REDIRECT;replace;${href};307;` });
  throw error;
});

type AsyncPage<TProps = any> = (props: TProps) => React.ReactNode | Promise<React.ReactNode>;

export async function renderAsyncPage(
  page: AsyncPage,
  props?: unknown,
) {
  const content = await page((props ?? {}) as any);
  return render(content);
}

if (typeof HTMLCanvasElement !== "undefined") {
  HTMLCanvasElement.prototype.getContext = vi.fn().mockReturnValue({
    clearRect: vi.fn(),
    fillRect: vi.fn(),
    beginPath: vi.fn(),
    moveTo: vi.fn(),
    lineTo: vi.fn(),
    stroke: vi.fn(),
    fill: vi.fn(),
    fillText: vi.fn(),
    strokeRect: vi.fn(),
    setLineDash: vi.fn(),
  }) as any;
}

beforeEach(() => {
  resetApiRuntimeSettingsCacheForTests();
  routerPush.mockReset();
  routerReplace.mockReset();
  routerRefresh.mockReset();
});

vi.mock("next/navigation", () => ({
  redirect: redirectMock,
  useRouter: () => ({
    push: routerPush,
    replace: routerReplace,
    prefetch: vi.fn(),
    refresh: routerRefresh,
  })
}));
