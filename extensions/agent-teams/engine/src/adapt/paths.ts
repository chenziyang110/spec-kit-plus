import { join } from "node:path";
import { type AdaptPathSet, type AdaptTarget } from "./contracts.js";
import { omxAdaptersDir } from "../utils/paths.js";

export function resolveAdaptPaths(
  cwd: string,
  target: AdaptTarget,
): AdaptPathSet {
  const adapterRoot = join(omxAdaptersDir(cwd), target);
  const reportsDir = join(adapterRoot, "reports");
  return {
    adapterRoot,
    configPath: join(adapterRoot, "adapter.json"),
    envelopePath: join(adapterRoot, "envelope.json"),
    reportsDir,
    probeReportPath: join(reportsDir, "probe.json"),
    statusReportPath: join(reportsDir, "status.json"),
  };
}
