# 图片内多素材自动切分与去背景工具

> 从一张“素材合集图 / asset sheet / 图标合集 / 2.5D 素材板”中自动识别多个独立元素，将它们逐个裁剪出来，并输出为透明背景 PNG。

**图片内多素材自动切分与去背景工具** 是一个面向素材整理、游戏美术、地图编辑器、UI 图标、AI 生成素材合集图的自动化处理工具。它可以把一张包含多个元素的图片自动拆分成多个独立素材，并尽可能去除背景、保留主体与阴影，最后生成透明 PNG 和 manifest 数据，方便后续导入 Eagle、游戏引擎、网页项目或素材管理系统。

这个工具最初用于处理 2.5D / isometric 地图素材合集图，例如河流、道路、桥梁、建筑、战争单位、科幻星图、仙侠宗门、现代城市素材等。但它并不局限于地图素材，也可以处理 UI 图标合集、道具素材合集、装饰元素合集、AI 生成素材板等图片。

---

## 适合处理什么图片？

适合：

- 一张图里包含多个独立素材的合集图
- 2.5D / isometric 游戏素材图
- 地图元素素材图
- 建筑、道路、桥梁、河流、海洋、山脉、树木等场景素材
- 战争沙盘单位、旗帜、营地、器械素材
- 科幻星图、空间站、飞船、星球、航线标记素材
- 仙侠宗门、阵法、灵脉、传送门、云桥等素材
- UI 图标、标记、特效、路线箭头、提示符合集图
- AI 生成的素材预览板或 asset sheet

不太适合：

- 多个素材之间严重粘连的图片
- 背景复杂、主体和背景颜色非常接近的图片
- 文字、编号、边框和素材贴得很近的图片
- 主体被遮挡或重叠严重的图片
- 需要像素级商业精修的最终美术资源

自动识别无法做到 100% 完美。遇到元素粘连、文字遮挡、阴影太淡、背景复杂、边框和素材连在一起的图片时，需要人工复查 `review_needed/` 和 `cropped/`。

---

## 核心功能

- 自动读取输入目录中的 PNG、JPG、JPEG、WEBP 图片
- 自动识别图片中的多个独立素材区域
- 自动过滤过小噪点、文字区域、页眉页脚、边框干扰
- 为每个素材单独裁剪，并保留 padding，避免裁切太紧
- 支持使用 `rembg` 批量去背景，输出透明 PNG
- 在未安装 `rembg` 时，可降级使用边缘背景色估计生成 alpha
- 支持输出统一尺寸，例如 512 或 1024
- 自动生成 manifest JSON，方便导入项目素材库
- 保留中间裁剪结果，便于人工检查
- 自动记录处理日志
- 识别失败或疑似异常的图片会进入 `review_needed/`
- 不删除、不覆盖原始图片

---

## 工作流程

```text
素材合集图
  ↓
自动检测独立元素区域
  ↓
按元素逐个裁剪
  ↓
保留安全边距 padding
  ↓
批量去背景
  ↓
输出透明 PNG
  ↓
生成 manifest JSON
  ↓
导入 Eagle / 游戏项目 / Web 项目 / 地图编辑器
```

---

## 目录结构

```text
tools/asset-extractor/
├── input_sheets/      # 放原始素材合集图
├── cropped/           # 自动裁剪出的中间结果
├── output_png/        # 最终透明 PNG 输出
├── review_needed/     # 自动识别失败或需要人工复查的图片
├── manifest/          # 自动生成的 manifest JSON
├── config.json        # 处理配置
├── extract_assets.py  # 主脚本
├── requirements.txt   # Python 依赖
└── README.md          # 工具说明
```

---

## 安装依赖

建议使用独立 Python 虚拟环境：

```bash
cd tools/asset-extractor
python -m venv .venv
```

Windows：

```bash
.venv\Scripts\activate
pip install -r requirements.txt
```

macOS / Linux：

```bash
source .venv/bin/activate
pip install -r requirements.txt
```

`requirements.txt` 建议包含：

```text
opencv-python
pillow
numpy
rembg
```

`rembg` 第一次运行时可能会下载模型，请保持网络可用。若暂未安装 `rembg`，脚本可以降级使用边缘背景色估计方式生成透明 alpha，但正式素材建议安装完整依赖后再运行。

---

## 放入素材合集图

把素材合集图放入：

```text
tools/asset-extractor/input_sheets/
```

支持格式：

```text
PNG / JPG / JPEG / WEBP
```

示例：

```text
input_sheets/
├── river_sheet.png
├── road_sheet.png
├── bridge_sheet.png
├── modern_city_assets.webp
├── sci_fi_space_map.jpg
└── xianxia_buildings.png
```

原图不会被删除或覆盖。

---

## 配置文件

编辑 `config.json`：

```json
{
  "category": "roads-waterways",
  "subCategory": "river",
  "prefix": "river",
  "padding": 36,
  "minArea": 8000,
  "maxArea": 1200000,
  "removeBackground": true,
  "outputSize": 512,
  "ignoreTextRegions": true,
  "commercialSafe": true,
  "licenseStatus": "ai-generated",
  "tags": ["2.5d", "isometric", "map", "river"]
}
```

### 配置项说明

| 字段 | 说明 |
|---|---|
| `category` | 素材大分类，例如 `roads-waterways`、`buildings`、`war` |
| `subCategory` | 素材子分类，例如 `river`、`bridge`、`city` |
| `prefix` | 输出文件名前缀，例如 `river` 会生成 `river_001.png` |
| `padding` | 裁剪时给素材四周保留的安全边距 |
| `minArea` | 过滤过小噪点的最小面积 |
| `maxArea` | 过滤过大区域的最大面积 |
| `removeBackground` | 是否启用背景移除 |
| `outputSize` | 输出图片建议尺寸，可用于统一素材大小 |
| `ignoreTextRegions` | 是否尝试忽略标题、编号、文字说明区域 |
| `commercialSafe` | 是否声明素材可商用 |
| `licenseStatus` | 授权状态，例如 `ai-generated`、`owned`、`licensed` |
| `tags` | 自动写入 manifest 的标签 |

---

## 常用分类示例

```text
river
road
bridge
ocean
building
terrain
nature
war
xianxia
sci-fi
modern-city
story-marker
ui-icon
effect
```

输出文件命名由 `prefix` 决定：

```text
river_001.png
river_002.png
river_003.png
```

---

## 运行脚本

基础运行：

```bash
cd tools/asset-extractor
python extract_assets.py
```

如果脚本支持参数，也可以临时覆盖分类和前缀：

```bash
python extract_assets.py --category roads-waterways --prefix river
```

示例：

```bash
python extract_assets.py --category buildings --prefix city
python extract_assets.py --category war --prefix cavalry
python extract_assets.py --category sci-fi --prefix planet
python extract_assets.py --category xianxia --prefix sect_building
```

---

## 输出结果

透明 PNG 输出在：

```text
tools/asset-extractor/output_png/
```

中间裁剪结果在：

```text
tools/asset-extractor/cropped/
```

识别失败或需要人工检查的图片会复制到：

```text
tools/asset-extractor/review_needed/
```

处理日志：

```text
tools/asset-extractor/processing.log
```

---

## Manifest 输出

脚本会生成：

```text
tools/asset-extractor/manifest/map_assets.generated.json
```

每条数据类似：

```json
{
  "id": "river_001",
  "name": "River 001",
  "category": "roads-waterways",
  "subCategory": "river",
  "spriteUrl": "/assets/map/isometric/roads-waterways/river_001.png",
  "thumbnail": "/assets/map/isometric/roads-waterways/river_001.png",
  "defaultWidth": 512,
  "defaultHeight": 512,
  "anchorX": 0.5,
  "anchorY": 0.8,
  "tags": ["2.5d", "isometric", "map", "river"],
  "licenseStatus": "ai-generated",
  "commercialSafe": true
}
```

这个 manifest 可以用于：

- 地图编辑器素材库
- 游戏项目资源表
- Web 前端资源列表
- Eagle 素材整理记录
- 自定义素材管理系统

---

## 导入 Open Word Studio 地图素材库

复制透明 PNG 到项目公开资源目录，例如：

```bash
mkdir -p ../../frontend/public/assets/map/isometric/roads-waterways
copy output_png\*.png ..\..\frontend\public\assets\map\isometric\roads-waterways\
```

macOS / Linux：

```bash
mkdir -p ../../frontend/public/assets/map/isometric/roads-waterways
cp output_png/*.png ../../frontend/public/assets/map/isometric/roads-waterways/
```

然后打开：

```text
tools/asset-extractor/manifest/map_assets.generated.json
```

将 `items` 合并到项目中的素材 manifest，例如：

```text
mapAssetManifest.ts
```

确认 `spriteUrl` 与实际公开目录一致：

```text
/assets/map/isometric/roads-waterways/river_001.png
```

---

## 导入 Eagle 的建议流程

这个工具适合和 Eagle 搭配使用：

```text
原始合集图
  ↓
本工具自动切分并去背景
  ↓
得到透明 PNG
  ↓
导入 Eagle
  ↓
按分类、标签、风格、授权状态管理
  ↓
再导出到项目素材目录
```

建议 Eagle 文件夹结构：

```text
Image Multi-Asset Extractor Output
├── 01_River
├── 02_Road
├── 03_Bridge
├── 04_Ocean
├── 05_Buildings
├── 06_War
├── 07_Xianxia
├── 08_SciFi
├── 09_ModernCity
└── 99_ReviewNeeded
```

建议标签：

```text
2.5d
isometric
transparent-png
map-asset
ai-generated
commercial-safe
needs-review
```

---

## 人工复查建议

自动识别不可能完全替代人工检查。建议重点检查：

- 一个素材是否被切成多块
- 多个素材是否被误裁到同一张图中
- 文字、编号、标题是否被误识别为素材
- 边框、装饰线是否被误识别为素材
- 阴影是否被裁掉
- 背景是否去除干净
- 主体边缘是否有白边、黑边、锯齿
- 输出尺寸是否过小或过大

常见问题处理：

| 问题 | 可能处理方式 |
|---|---|
| 一个素材被切成多块 | 增大 morphology close，或人工修图后重跑 |
| 多个素材粘在一起 | 降低合集图复杂度，或手工切分 |
| 文字被识别为素材 | 提高 `minArea`，开启 `ignoreTextRegions` |
| 素材漏检 | 降低 `minArea` 或调整背景容差 |
| 背景去除不干净 | 确认已安装 `rembg`，或换更干净的原图 |
| 阴影被去掉 | 减弱背景移除强度，或保留带阴影版本 |

---

## 适合 GitHub 的项目名称建议

你可以把仓库命名为：

```text
image-multi-asset-extractor
```

或：

```text
multi-asset-extractor-bg-remover
```

或：

```text
asset-sheet-extractor
```

推荐仓库描述：

```text
Automatically split multi-object asset sheets into individual transparent PNG assets with background removal and manifest generation.
```

中文描述：

```text
一个用于将图片内多个素材自动切分为独立透明 PNG，并生成素材 manifest 的自动化工具。
```

---

## GitHub 发布建议

建议仓库结构：

```text
image-multi-asset-extractor/
├── input_sheets/
├── cropped/
├── output_png/
├── review_needed/
├── manifest/
├── config.json
├── extract_assets.py
├── requirements.txt
├── README.md
├── LICENSE
└── .gitignore
```

建议 `.gitignore`：

```gitignore
.venv/
__pycache__/
*.pyc
processing.log
input_sheets/*
cropped/*
output_png/*
review_needed/*
manifest/*.json
!input_sheets/.gitkeep
!cropped/.gitkeep
!output_png/.gitkeep
!review_needed/.gitkeep
!manifest/.gitkeep
```

这样可以避免把你自己的素材图和输出结果直接上传到 GitHub。

---

## 注意事项与授权提醒

`commercialSafe: true` 只表示你声明这些素材可商用或由你生成/拥有。导入正式素材库或商业项目之前，请确认素材来源授权。

如果你的素材来自 AI 生成、第三方素材包、开源项目、付费素材网站或参考图，请分别记录来源和授权状态。不要把 `reference-only`、`not-for-commercial`、`copyright-risk` 的素材直接用于商业项目。

---

## Limitations

- The extraction result depends heavily on image layout and background cleanliness.
- Complex backgrounds may reduce segmentation accuracy.
- Text labels, borders, and decorative frames may be detected as assets.
- Overlapping or touching objects may be extracted as one object.
- Some outputs may still require manual cleanup.
- This tool is designed to speed up asset processing, not to replace final art review.

---

## License

You can choose a license based on how you want to publish the project.

Recommended open-source license:

```text
MIT License
```

If you include generated example images, make sure those images are also allowed to be redistributed.

---

## Roadmap

Planned improvements:

- Better text and label filtering
- SAM / Segment Anything integration
- Batch mode for different categories
- GUI desktop version
- Drag-and-drop image input
- Preview before exporting
- Automatic Eagle import helper
- Direct export to Open Word Studio map asset manifest
- Transparent background quality scoring
- Manual correction UI for failed detections

---

## Summary

**图片内多素材自动切分与去背景工具** 可以帮助你把素材合集图快速拆成独立透明 PNG。它特别适合处理 AI 生成的 asset sheet、2.5D 地图素材、游戏素材、UI 图标和各种图片内多元素资源。

它不是一个完全替代人工美术处理的工具，而是一个用于批量整理素材、加快资产入库、减少重复劳动的自动化工具。
