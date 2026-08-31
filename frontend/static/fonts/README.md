# Self-hosted fonts (required — spec 10)

Fonts are **not** fetched from any CDN at runtime. Put these `.woff2` files here;
`src/app.css` references them by exact name. Until they exist the UI falls back to
Calibri / system serif, so the app still works.

| File | Source (OFL, free to self-host) |
|---|---|
| `carlito-regular.woff2` | Carlito — https://github.com/googlefonts/carlito (metric-compatible Calibri) |
| `carlito-bold.woff2` | Carlito Bold |
| `carlito-italic.woff2` | Carlito Italic |
| `tirobangla-regular.woff2` | Tiro Bangla — https://github.com/googlefonts/tirotamil (Tiro family) |
| `tirobangla-italic.woff2` | Tiro Bangla Italic |

Convert TTF → WOFF2 with `woff2_compress` or `fonttools`:

```
uvx fonttools ttLib.woff2 compress Carlito-Regular.ttf -o carlito-regular.woff2
```
