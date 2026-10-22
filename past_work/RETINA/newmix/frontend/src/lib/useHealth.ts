"use client";

import { useCallback, useEffect, useState } from "react";
import { api, type Health } from "./api";

export type HealthState =
  | { phase: "loading" }
  | { phase: "offline"; message: string }
  | { phase: "ready"; health: Health };

export function useHealth(pollMs = 20000) {
  const [state, setState] = useState<HealthState>({ phase: "loading" });

  const check = useCallback(async () => {
    try {
      setState({ phase: "ready", health: await api.health() });
    } catch (e) {
      setState({ phase: "offline", message: e instanceof Error ? e.message : "offline" });
    }
  }, []);

  useEffect(() => {
    const first = setTimeout(check, 0);
    const t = setInterval(check, pollMs);
    return () => {
      clearTimeout(first);
      clearInterval(t);
    };
  }, [check, pollMs]);

  return { state, refresh: check };
}

export function serviceSummary(h: Health) {
  const s = h.services;
  const items = [
    { key: "glaucoma_oct", label: "OCT model", ok: s.glaucoma_oct.ready },
    { key: "glaucoma_clinical", label: "Clinical model", ok: s.glaucoma_clinical.ready },
    { key: "glaucoma_multimodal", label: "Multimodal (GAMMA)", ok: s.glaucoma_multimodal.ready },
    { key: "diabetes", label: "Diabetes models", ok: s.diabetes.vessels && s.diabetes.hba1c },
  ];
  return { items, allOk: items.every((i) => i.ok), okCount: items.filter((i) => i.ok).length };
}
