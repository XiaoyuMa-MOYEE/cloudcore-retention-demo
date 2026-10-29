# Cloudflare Deployment Note / Cloudflare 部署说明

The active Worker configuration and proxy are in `web/wrangler.jsonc` and `web/api-proxy.js`. Workers Builds Root directory must be `web`; do not use this documentation folder as project root. / 实际 Worker 配置和代理位于 `web/wrangler.jsonc`、`web/api-proxy.js`。Workers Builds Root directory 必须设为 `web`，不得将本说明目录作为项目根目录。

Build/deploy settings and persistent backend setup are in [`../../docs/deployment/README.md`](../../docs/deployment/README.md). No production deployment has been run. / 构建、部署设置及持久化后端配置见部署手册；尚未执行生产部署。
