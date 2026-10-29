import { cp, mkdir, rm } from "node:fs/promises";
import { resolve } from "node:path";
import { fileURLToPath } from "node:url";

const projectRoot = resolve(fileURLToPath(new URL("..", import.meta.url)));
const moduleRoot = resolve(projectRoot, "python_modules");
const coreTarget = resolve(moduleRoot, "src");

await mkdir(moduleRoot, { recursive: true });
await rm(coreTarget, { recursive: true, force: true });
await cp(resolve(projectRoot, "src"), coreTarget, {
  recursive: true,
  filter: (source) => !source.includes("__pycache__") && !source.endsWith(".pyc"),
});
