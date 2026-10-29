# Cloudflare Build Path Fix — 2026-10-30

## English

### Issue
Cloudflare Workers Builds runs `npx wrangler deploy` from the configured `web/` root directory. Wrangler loads the repository-level `wrangler.jsonc`, then runs its custom build command from `web/`. The configured command `node scripts/prepare-worker-python.mjs` therefore looked for the script under `web/scripts/` and failed with `MODULE_NOT_FOUND`.

### Change
Added `web/scripts/prepare-worker-python.mjs` as a thin wrapper importing the canonical repository-root script. This lets Wrangler resolve the command from Cloudflare's `web/` build root while keeping one implementation of the Python bundle preparation logic. Local deployment from the repository root continues to use that same canonical script.

### Verification
- `npm run build` from `web/`: passed.
- `npx wrangler deploy --dry-run` from `web/`: custom Python build completed, 486 Python modules and 6 static assets were bundled, dry-run exited successfully. Local Wrangler emitted a sandbox log-file permission warning after completing the bundle; this did not reproduce the missing-script failure.
- Cloudflare production deployment and live API execution were not performed by this local verification.

## 中文

### 问题
Cloudflare Workers Builds 从配置的 `web/` 根目录运行 `npx wrangler deploy`。Wrangler 会读取仓库根目录的 `wrangler.jsonc`，但自定义构建命令在 `web/` 目录执行。因此原命令 `node scripts/prepare-worker-python.mjs` 会去 `web/scripts/` 查找脚本并报 `MODULE_NOT_FOUND`。

### 修改
新增 `web/scripts/prepare-worker-python.mjs` 作为轻量包装脚本，导入仓库根目录中的规范脚本。这样 Wrangler 可以从 Cloudflare 的 `web/` 构建根目录解析命令，同时只保留一份 Python 打包逻辑；从仓库根目录进行的本地部署仍使用同一规范脚本。

### 验证
- 在 `web/` 执行 `npm run build`：通过。
- 在 `web/` 执行 `npx wrangler deploy --dry-run`：Python 自定义构建成功，打包了 486 个 Python 模块和 6 个静态资源，dry-run 成功结束。本地 Wrangler 在打包完成后报告沙箱日志文件权限警告；未再出现脚本缺失错误。
- 本地验证不包含 Cloudflare 生产部署或线上 API 调用。
