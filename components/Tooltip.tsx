"use client";

import { useCallback, useState, type FocusEvent, type PointerEvent, type ReactNode } from "react";

type Tip = { x: number; y: number; content: ReactNode } | null;

/** Pointer- and keyboard-driven tooltip. `bind(content)` returns the handlers to spread on a mark. */
export function useTooltip() {
  const [tip, setTip] = useState<Tip>(null);

  const bind = useCallback(
    (content: ReactNode) => ({
      onPointerEnter: (e: PointerEvent) => setTip({ x: e.clientX, y: e.clientY, content }),
      onPointerMove: (e: PointerEvent) => setTip({ x: e.clientX, y: e.clientY, content }),
      onPointerLeave: () => setTip(null),
      onFocus: (e: FocusEvent<HTMLElement>) => {
        const r = e.currentTarget.getBoundingClientRect();
        setTip({ x: r.left + r.width / 2, y: r.top, content });
      },
      onBlur: () => setTip(null),
    }),
    [],
  );

  const view = tip ? (
    <div
      className="tooltip"
      role="tooltip"
      style={{
        left: Math.min(tip.x + 14, (typeof window === "undefined" ? 9999 : window.innerWidth) - 280),
        top: tip.y + 18,
      }}
    >
      {tip.content}
    </div>
  ) : null;

  return { bind, view };
}
