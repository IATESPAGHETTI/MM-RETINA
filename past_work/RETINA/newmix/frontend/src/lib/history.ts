"use client";

import { useSyncExternalStore } from "react";

/** Session history kept only in this browser (localStorage). Stores summaries, never images. */
export interface RunRecord {
  id: string;
  at: number;
  module: "glaucoma" | "diabetes" | "multimodal";
  title: string;
  result: string;
  confidence?: number;
  inputs: string;
  patientId?: string;
}

const KEY = "retina-suite:history:v1";
const MAX = 25;
let cache: RunRecord[] | null = null;
const subs = new Set<() => void>();

function read(): RunRecord[] {
  if (cache) return cache;
  try {
    cache = JSON.parse(localStorage.getItem(KEY) || "[]") as RunRecord[];
  } catch {
    cache = [];
  }
  return cache;
}

export function addRun(r: Omit<RunRecord, "id" | "at">) {
  const next = [{ ...r, id: crypto.randomUUID(), at: Date.now() }, ...read()].slice(0, MAX);
  cache = next;
  let persisted = false;
  try {
    localStorage.setItem(KEY, JSON.stringify(next));
    persisted = true;
  } catch {
    /* storage blocked: history just won't persist */
  }
  subs.forEach((f) => f());
  return persisted;
}

export function clearRuns() {
  cache = read().filter((run) => run.patientId);
  try {
    if (cache.length) localStorage.setItem(KEY, JSON.stringify(cache));
    else localStorage.removeItem(KEY);
  } catch {
    /* ignore */
  }
  subs.forEach((f) => f());
}

const EMPTY: RunRecord[] = [];
export function useRuns(): RunRecord[] {
  return useSyncExternalStore(
    (cb) => {
      subs.add(cb);
      return () => subs.delete(cb);
    },
    read,
    () => EMPTY,
  );
}
