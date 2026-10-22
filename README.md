# mos-repo

MOS 系统专属软件源：壁纸源 + MOS 应用软件包，服务于 [MOS](https://github.com/wurong10001/MOS)（网页桌面）与 [mos-android](https://github.com/wurong10001/mos-android)。

## 目录结构

- `uploads/wallpaper/` — 壁纸源
- `uploads/mosapp/` — MOS 应用 / 软件包（.wasm / .apk / .zip …）
- `index.json` / `index.tsv` — 文件索引（自动生成，请勿手动编辑）
- `scripts/build_index.py` — 索引生成脚本（仅标准库）
- `.github/workflows/rebuild-index.yml` — 推送 uploads/ 新文件时自动重建索引

## 用法

1. 把文件放进 `uploads/<分类>/`（如 `uploads/mosapp/`）并推送，Actions 会自动更新索引（公共仓库首次需在 Actions 页批准一次工作流）。
2. 客户端拉取索引：
   - `https://raw.githubusercontent.com/wurong10001/mos-repo/main/index.json`
   - 镜像：`https://cdn.jsdelivr.net/gh/wurong10001/mos-repo@main/index.json`
3. 下载用 `files[].url`（备用 `files[].cdn`），完成后校验 `files[].sha256`。

索引字段：`path / name / category / ext / type / size / sha256 / updated_at / url / cdn`。

## 本地手动重建

```bash
python3 scripts/build_index.py
```

## 内置客户端

- MOS 网页端：`public/assets/repo.js` + 软件源页面 `/repo.html`
- mos-android：`app/src/main/cpp/repo_client.h/.cpp`（下载至应用私有目录 `user/tmp`）
