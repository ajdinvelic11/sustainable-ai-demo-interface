import type { DemoRunState } from "../types/api";
import FinalResults from "./FinalResults";

interface FinalResultsPanelProps {
  run: DemoRunState;
  onStartNew: () => void;
}

export default function FinalResultsPanel({ run, onStartNew }: FinalResultsPanelProps) {
  return <FinalResults run={run} onStartNew={onStartNew} />;
}
