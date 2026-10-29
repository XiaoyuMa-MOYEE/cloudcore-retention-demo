import { cp, mkdir, rm } from "node:fs/promises";
import { resolve } from "node:path";
import { fileURLToPath } from "node:url";

const projectRoot = resolve(fileURLToPath(new URL("..", import.meta.url)));
const moduleRoot = resolve(projectRoot, "python_modules");
const coreTarget = resolve(moduleRoot, "src");
const appTarget = resolve(moduleRoot, "cloudflare_app.py");

await mkdir(moduleRoot, { recursive: true });
const copyPackage = async (source, target) => {
  await rm(target, { recursive: true, force: true });
  await cp(source, target, {
    recursive: true,
    filter: (path) => !path.includes("__pycache__") && !path.endsWith(".pyc"),
  });
};

await Promise.all([
  copyPackage(resolve(projectRoot, "src"), coreTarget),
  cp(resolve(projectRoot, "backend", "cloudflare_app.py"), appTarget),
]);
