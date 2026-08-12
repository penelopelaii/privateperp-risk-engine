"use client";

import V1InputForm from "@/components/V1InputForm";
import V1Outputs from "@/components/V1Outputs";
import ViabilityFrontier from "@/components/ViabilityFrontier";
import { evaluateRiskV1 } from "@/lib/api";
import { DEFAULT_PRESET_V1, PRESETS_V1 } from "@/lib/presetsV1";
import type { MarketState, RiskOutputsV1 } from "@/lib/typesV1";
import { useCallback, useEffect, useState } from "react";

const DEBOUNCE_MS = 150;

export default function V1Console() {
  const [state, setState] = useState<MarketState>(DEFAULT_PRESET_V1.state);
  const [activePresetId, setActivePresetId] = useState<string | null>(
    DEFAULT_PRESET_V1.id,
  );
  const [outputs, setOutputs] = useState<RiskOutputsV1 | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  useEffect(() => {
    const controller = new AbortController();
    const timer = setTimeout(async () => {
      setPending(true);
      try {
        const response = await evaluateRiskV1(state, controller.signal);
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
  }, [state]);

  const handleChange = useCallback((key: keyof MarketState, value: number) => {
    setActivePresetId(null);
    setState((current) => ({ ...current, [key]: value }));
  }, []);

  const handlePreset = useCallback((presetId: string) => {
    const preset = PRESETS_V1.find((candidate) => candidate.id === presetId);
    if (!preset) return;
    setActivePresetId(preset.id);
    setState(preset.state);
  }, []);

  return (
    <>
      <ViabilityFrontier state={state} outputs={outputs} />
      <div className="layout">
        <V1InputForm
          state={state}
          activePresetId={activePresetId}
          onChange={handleChange}
          onPreset={handlePreset}
        />
        <V1Outputs outputs={outputs} error={error} pending={pending} />
      </div>
    </>
  );
}
