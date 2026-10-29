# Cloudflare Static Asset Routing Fix — 2026-10-30

## English

### Diagnosis
The deployed `/api/health` endpoint returned `200`, while `/` returned `Internal Server Error`. This confirmed that the Worker and FastAPI were reachable, but the homepage request failed in the Python catch-all route that manually proxied static assets. Wrangler had `assets.run_worker_first: true`, forcing every static request through that proxy.

### Change
Set `assets.run_worker_first` to `["/api/*"]`. API requests continue to reach the Python Worker first; the homepage, JavaScript, and CSS are served directly by Cloudflare Static Assets, with the existing SPA fallback. This follows Cloudflare's selective Worker-first routing behavior.

### Verification
- `web/dist/index.html` exists and references the built JavaScript and CSS assets.
- Wrangler dry-run confirms the configuration parses and bundles the Worker and assets.
- Live confirmation requires the next automatic Cloudflare deployment. Expected checks: `/api/health` returns `status: ok`; `/` serves the React app.

## 中文

### 诊断
线上 `/api/health` 返回 `200`，但 `/` 返回 `Internal Server Error`。这说明 Worker/FastAPI 可访问，错误出现在 Python catch-all 路由手动代理静态文件的路径。Wrangler 的 `assets.run_worker_first: true` 让所有静态请求都先经过该代理。

### 修改
将 `assets.run_worker_first` 改为 `["/api/*"]`。API 请求仍优先进入 Python Worker；首页、JavaScript 和 CSS 改由 Cloudflare Static Assets 直接提供，并使用现有 SPA fallback。这使用 Cloudflare 支持的按路径选择 Worker 优先模式。

### 验证
- `web/dist/index.html` 存在，并引用已构建的 JavaScript 与 CSS 文件。
- Wrangler dry-run 确认配置可解析，并可打包 Worker 和静态资源。
- 线上结果须等待下一次 Cloudflare 自动部署后确认。预期检查：`/api/health` 返回 `status: ok`，`/` 返回 React 页面。
