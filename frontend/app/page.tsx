"use client";

import OutputCards from "@/components/OutputCards";
import RiskInputForm from "@/components/RiskInputForm";
import V1Console from "@/components/V1Console";
import { evaluateRisk } from "@/lib/api";
import { DEFAULT_PRESET, PRESETS } from "@/lib/presets";
import type { RiskInputs, RiskOutputs } from "@/lib/types";
import { useCallback, useEffect, useState } from "react";

const DEBOUNCE_MS = 150;

type Engine = "v1" | "v0";

function V0Console() {
  const [inputs, setInputs] = useState<RiskInputs>(DEFAULT_PRESET.inputs);
  const [activePresetId, setActivePresetId] = useState<string | null>(
    DEFAULT_PRESET.id,
  );
  const [outputs, setOutputs] = useState<RiskOutputs | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  useEffect(() => {
    const controller = new AbortController();
    const timer = setTimeout(async () => {
      setPending(true);
      try {
        const response = await evaluateRisk(inputs, controller.signal);
        setOutputs(response.outputs);
        setError(null);
      } catch {
        if (!controller.signal.aborted) {
          setError("Could not reach the risk engine API.");
        }
      } finally {
        if (!controller.signal.aborted) {
          setPending(false);
        }
      }
    }, DEBOUNCE_MS);

    return () => {
      clearTimeout(timer);
      controller.abort();
    };
  }, [inputs]);

  const handleChange = useCallback((key: keyof RiskInputs, value: number) => {
    setActivePresetId(null);
    setInputs((current) => ({ ...current, [key]: value }));
  }, []);

  const handlePreset = useCallback((presetId: string) => {
    const preset = PRESETS.find((candidate) => candidate.id === presetId);
    if (!preset) return;
    setActivePresetId(preset.id);
    setInputs(preset.inputs);
  }, []);

  return (
    <div className="layout">
      <RiskInputForm
        inputs={inputs}
        activePresetId={activePresetId}
        onChange={handleChange}
        onPreset={handlePreset}
      />
      <OutputCards outputs={outputs} error={error} pending={pending} />
    </div>
  );
}

export default function Home() {
  const [engine, setEngine] = useState<Engine>("v1");

  return (
    <main>
      <header className="masthead">
        <p className="eyebrow">
          PrivatePerp Risk Engine &middot; research prototype &middot; synthetic
          data only
        </p>
        <h1>When Should a Perp Stop Being a Perp?</h1>
        <p className="question">
          Mapping the viability frontier of continuous margining for illiquid
          underlyings.
        </p>
      </header>

      <nav className="engine-tabs" aria-label="Engine version">
        <button
          type="button"
          className={engine === "v1" ? "engine-tab active" : "engine-tab"}
          aria-pressed={engine === "v1"}
          onClick={() => setEngine("v1")}
        >
          V1 Adaptive Risk Engine
          <em>Five risk dimensions, and an answer of &ldquo;no&rdquo;</em>
        </button>
        <button
          type="button"
          className={engine === "v0" ? "engine-tab active" : "engine-tab"}
          aria-pressed={engine === "v0"}
          onClick={() => setEngine("v0")}
        >
          V0 Composite Score
          <em>The heuristic v1 replaced, kept for comparison</em>
        </button>
      </nav>

      {engine === "v1" ? <V1Console /> : <V0Console />}
    </main>
  );
}
