"use client";

import V1InputForm from "@/components/V1InputForm";
import V1Outputs from "@/components/V1Outputs";
import ViabilityFrontier from "@/components/ViabilityFrontier";
import { evaluateFrontierV1, evaluateRiskV1 } from "@/lib/api";
import { DEFAULT_PRESET_V1, PRESETS_V1 } from "@/lib/presetsV1";
import type {
  FrontierV1Response,
  MarketState,
  RiskOutputsV1,
} from "@/lib/typesV1";
import { nonAxisFrontierFingerprint } from "@/lib/typesV1";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";

const EVALUATE_DEBOUNCE_MS = 150;
const FRONTIER_DEBOUNCE_MS = 250;

export default function V1Console() {
  const [state, setState] = useState<MarketState>(DEFAULT_PRESET_V1.state);
  const [activePresetId, setActivePresetId] = useState<string | null>(
    DEFAULT_PRESET_V1.id,
  );
  const [outputs, setOutputs] = useState<RiskOutputsV1 | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  const [grid, setGrid] = useState<FrontierV1Response | null>(null);
  const [frontierError, setFrontierError] = useState<string | null>(null);
  const [frontierPending, setFrontierPending] = useState(false);

  const stateRef = useRef(state);
  stateRef.current = state;

  const frontierFingerprint = useMemo(
    () => nonAxisFrontierFingerprint(state),
    [state],
  );

  // Live assessment: full MarketState on every change.
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
    }, EVALUATE_DEBOUNCE_MS);

    return () => {
      clearTimeout(timer);
      controller.abort();
    };
  }, [state]);

  // Frontier map: only when non-axis inputs (or policy) change.
  useEffect(() => {
    const controller = new AbortController();
    const timer = setTimeout(async () => {
      setFrontierPending(true);
      try {
        const response = await evaluateFrontierV1(
          stateRef.current,
          controller.signal,
        );
        setGrid(response);
        setFrontierError(null);
      } catch {
        if (!controller.signal.aborted) {
          setFrontierError("Could not compute the viability frontier.");
        }
      } finally {
        if (!controller.signal.aborted) {
          setFrontierPending(false);
        }
      }
    }, FRONTIER_DEBOUNCE_MS);

    return () => {
      clearTimeout(timer);
      controller.abort();
    };
  }, [frontierFingerprint]);

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
      <ViabilityFrontier
        state={state}
        outputs={outputs}
        grid={grid}
        pending={frontierPending}
        error={frontierError}
      />
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
