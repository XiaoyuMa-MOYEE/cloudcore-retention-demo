# Cloudflare Route / Cloudflare 路由

`api-proxy.js` forwards only the configured `cloudcore.moyee.uk/api/*` route to the standalone FastAPI backend. It contains no credentials and does not implement customer logic. Set `BACKEND_ORIGIN` to the API host before deployment, and verify the hostname and path pattern before running Wrangler. / `api-proxy.js` 只将已配置的 `cloudcore.moyee.uk/api/*` 路由转发至独立 FastAPI 后端；不含密钥，也不实现客户业务逻辑。部署前设置 API 主机 `BACKEND_ORIGIN`，并核对 hostname 与 path pattern。

Deployment commands and the Pages setup are documented in [`../../docs/deployment/README.md`](../../docs/deployment/README.md). No deployment has been run. / Pages 设置与部署步骤见部署手册；目前尚未执行部署。
