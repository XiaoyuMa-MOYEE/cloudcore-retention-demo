import { copyFile, mkdir } from "node:fs/promises";
import { resolve } from "node:path";
import { fileURLToPath } from "node:url";

const webRoot = resolve(fileURLToPath(new URL("..", import.meta.url)));
const projectRoot = resolve(webRoot, "..");
const publicDir = resolve(webRoot, "public");
await mkdir(publicDir, { recursive: true });
await Promise.all([
  copyFile(resolve(projectRoot, "config.yaml"), resolve(publicDir, "cloudcore-config.yaml")),
  copyFile(resolve(projectRoot, "data/input/模拟数据.csv"), resolve(publicDir, "simulated-data.csv")),
]);
