# PDF2plus

**一句话**：Windows 上的离线 PDF 工具箱——合并、拆分、转换、压缩、水印、加密等，克隆仓库后即可直接双击运行。

| 项目 | 说明 |
|------|------|
| 产品名 | PDF2plus（展示名 PDF2+） |
| 当前版本 | V4.0.9 |
| 平台 | Windows 10 / 11（64 位） |
| 作者 | 雪部湾扁橙（JasonCZ313） |
| 远程仓库 | https://github.com/JasonCZ313/PDF2plus.git |
| 许可证 | MIT |

---

## 🚀 最快开始（普通用户）

克隆本仓库后，**不要找别的地方**，直接打开：

```text
dist\package\PDF2plus.exe
```

双击即可使用，**无需安装 Python、无需再打包、无需联网**（OCR 模型已随包内置）。

> 目录提示：`dist/package/` 里是完整可运行程序；旁边的 `runtime/` 是主程序运行库，请勿单独删除或挪走。

---

## ✨ 功能一览

- **合并 PDF**：多文件按顺序合并
- **拆分 PDF**：按页数 / 份数 / 自定义范围拆分
- **PDF ↔ 图片**：导出为 PNG/JPG 等；图片合成 PDF
- **转 Word**：PDF 转 DOCX（含可选 OCR）
- **压缩 PDF**：可选目标体积档位
- **水印与页码**：文字/图片水印、颜色、透明度、实时预览
- **页面管理**：删页、排序、旋转、提取（带缩略图预览）
- **安全**：加密 / 解密、权限相关选项
- **界面**：浅色/深色主题、中英文切换、字号档位、窗口自适应

---

## 📦 仓库里有什么

### 给「直接用」的人

| 路径 | 作用 |
|------|------|
| **`dist/package/PDF2plus.exe`** | **唯一推荐的启动入口** |
| `dist/package/runtime/` | 主程序与依赖（随启动器一起用） |

### 给「开发 / 二次打包」的人

| 路径 | 作用 |
|------|------|
| `app/` | 全部业务与界面源码 |
| `main.py` | 源码调试入口 |
| `launcher.py` | 薄启动器源码 |
| `assets/` | 图标、OCR 模型 |
| `requirements.txt` | Python 依赖 |
| `run_build.py` / `build.bat` | 一键打包 |
| `*.spec` | PyInstaller 配置 |
| `更新日志.txt` | 版本变更记录 |

### 不会放进仓库的内容

`build/`、`qa_audit/`、用户 `data/`、重复的中间目录等（见 `.gitignore`）。这些对日常使用与二次开发不是必需的。

---

## 🗂 源码结构（简图）

```text
PDF2plus/
├── dist/package/PDF2plus.exe   ← 用户双击这里
├── dist/package/runtime/       ← 主程序运行时
├── app/
│   ├── gui.py                  ← 主窗口
│   ├── feature_dialogs.py      ← 各功能对话框
│   ├── pdf_*.py                ← 合并/拆分/转换/压缩/水印/安全等
│   ├── i18n.py                 ← 中英文
│   ├── ui_theme.py / ui_scale.py
│   └── config.py               ← 版本号与应用名
├── main.py                     ← python main.py
├── launcher.py                 ← 启动器逻辑
├── run_build.py / build.bat    ← 打包
├── requirements.txt
├── README.md                   ← 本说明
├── LICENSE                     ← MIT 许可证
└── 更新日志.txt
```

---

## 🛠 开发者：源码运行

1. 安装 **Python 3.10+（64 位）**
2. 在项目根目录执行：

```bat
python -m pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
python main.py
```

---

## 🛠 开发者：重新打包

```bat
build.bat
```

或：

```bat
python run_build.py
```

成功后入口仍是：

```text
dist\package\PDF2plus.exe
```

可选安装器：

```bat
python run_build.py --installer
```

可选网盘分发物：`dist\app_payload.zip`（默认不进 Git）。

---

## ❓ 常见问题

**Q：找不到启动器？**  
A：路径固定为 `dist\package\PDF2plus.exe`。不要运行 `dist` 根目录下可能存在的临时/中间 exe。

**Q：杀毒软件报毒？**  
A：正式发布包默认未做 Windows 代码签名，SmartScreen / 杀毒可能提示「未知发布者」。可将 `dist\package` 加入白名单，选择「仍要运行」，或自行 `build.bat` 打包。需要安装向导时：`python run_build.py --installer`。

**Q：OCR / 转 Word 很慢？**  
A：首次加载 OCR 引擎会稍慢；之后同进程内会复用。纯文本 PDF 转换通常更快。

**Q：克隆很大？**  
A：仓库包含可运行包（约数百 MB），换来的是「克隆即可用」。若你只关心源码，可只查看 `app/` 与 `main.py`。当前程序版本为 V4.0.9（以标题栏为准）。

**Q：如何确认版本？**  
A：打开程序后看标题栏或状态栏版本号（应为 V4.0.9 或更新日志中的对应版本）。

---

## 📄 许可证与声明

本项目以 **MIT** 许可证开源（见根目录 `LICENSE`）。面向个人与办公场景的离线 PDF 处理。请遵守当地法律，仅处理您有权操作的文件。第三方库（PyQt5、PyMuPDF、RapidOCR 等）遵循各自开源许可证。

---

## 🔗 远程地址

```text
https://github.com/JasonCZ313/PDF2plus.git
```

更细的版本说明见仓库根目录 `更新日志.txt`。

---

# PDF2plus (English)

**In one line:** An offline Windows PDF toolbox—merge, split, convert, compress, watermark, encrypt, and more. After cloning, double-click the launcher and go.

| Item | Detail |
|------|--------|
| Product | PDF2plus (brand mark: PDF2+) |
| Version | V4.0.9 |
| Platform | Windows 10 / 11 (64-bit) |
| Author | 雪部湾扁橙（JasonCZ313） |
| Remote | https://github.com/JasonCZ313/PDF2plus.git |
| License | MIT |

---

## 🚀 Quick start (end users)

After cloning, open this file only:

```text
dist\package\PDF2plus.exe
```

No Python install, no rebuild, no network required for basic use (OCR models are bundled).

> Keep the whole `dist\package\` folder intact. The `runtime\` directory next to the exe is required.

---

## ✨ Features

- Merge / split PDFs  
- PDF ↔ images; PDF → Word (optional OCR)  
- Compress with target-size options  
- Watermark & page numbers with live preview  
- Page manager (delete / reorder / rotate / extract)  
- Encrypt / decrypt  
- Light/dark theme, ZH/EN UI, font size presets, responsive layout  

---

## 📦 What’s in the repo

**Run immediately:** `dist\package\PDF2plus.exe` (+ `runtime\`)

**Develop / rebuild:** `app\`, `main.py`, `launcher.py`, `assets\`, `requirements.txt`, `run_build.py`, `build.bat`, `*.spec`

**Not in Git:** build caches, QA folders, personal `data\`, duplicate intermediate outputs (see `.gitignore`).

---

## 🗂 Layout (short)

```text
dist/package/PDF2plus.exe   ← double-click this
app/                        ← source
main.py / launcher.py       ← dev entry & thin launcher
run_build.py / build.bat    ← packaging
README.md / LICENSE / 更新日志.txt
```

---

## 🛠 Run from source

```bat
python -m pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
python main.py
```

Requires Python 3.10+ (64-bit).

---

## 🛠 Rebuild the package

```bat
build.bat
```

Output launcher:

```text
dist\package\PDF2plus.exe
```

Optional: `python run_build.py --installer`

---

## FAQ

**Where is the launcher?**  
Always `dist\package\PDF2plus.exe`.

**Antivirus warning?**  
Unsigned release may trigger SmartScreen. Whitelist `dist\package`, choose Run anyway, or rebuild locally. Optional installer: `python run_build.py --installer`.

**Why is the clone large?**  
The repo ships a ready-to-run package so users don’t need to build. Current app version is V4.0.9 (see window title).

**How do I check the version?**  
Window title / status bar (expect V4.0.9 or the version listed in `更新日志.txt`).

---

## License / notice

Released under the **MIT** License (see `LICENSE`). For personal and office offline PDF work. Only process files you are allowed to handle. Third-party libraries keep their own licenses.

Changelog: `更新日志.txt` in the repo root.
