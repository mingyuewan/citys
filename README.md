# 深圳湾 · 空中之岛

把深圳湾后海一带做成一座漂在云海上的 3D 城市岛屿。纯浏览器运行，渲染引擎是手写的 WebGL2，不依赖任何库；数据全部内置在一个 HTML 文件里，可离线打开。

直接用浏览器打开 `index.html` 即可（开启 GitHub Pages 后也可在线访问）。

## 场景里有什么

- **城市**：真实 OSM 路网（4,799 条道路）、11 座真实地标（坐标与高度来自维基百科）、按真实街区生成的约 2,000 栋楼（写字楼、住宅、城中村、在建楼）
- **浮空岛**：不规则岛体、岩层与垂岩、深圳湾海水从岛缘泻成的瀑布、云海、10 座小浮岛
- **街道**：车道线、斑马线、转向箭头、红绿灯、公交站、路灯、立体车流、路边与停车场停车、行人和骑行者
- **建筑细节**：裙楼、退台空中花园、避难层、大堂雨棚、空调外机、防盗网、窗后房间（interior mapping）
- **空中**：航班、直升机、飞艇、热气球、白鹭、配送无人机、塔吊；夜里有 900 架无人机灯光秀、孔明灯、探照灯
- **时间**：可拖动时间滑块，日照、阴影、灯光随时间变化

## 操作

拖动平移 · 右键 / Shift 拖动旋转 · 滚轮缩放 · 点击楼体查看信息。快捷键：`F` 空中漫游、`N` 日夜、`R` 环绕、`H` 总览、`C` 云层、`G` 显示/隐藏生成楼体。

## 目录

| 路径 | 说明 |
| - | - |
| `index.html` | 组装好的页面（数据已内置） |
| `src/city.src.html` | 页面源码，`/*__SZDATA__*/` 处注入数据 |
| `data/szbay.json` | 数据集：道路、海陆掩膜、用地掩膜、楼体、地标、树木、球场等 |
| `tools/build_data.py` | 数据管线（OSM 路网 shapefile → `data/szbay.json`） |
| `tools/assemble3.py` | 把源码和数据组装成 `index.html` |
| `tools/build.sh` | 一键重建 |
| `tools/record.py` | 逐帧录制演示视频（Playwright + 无头 Chromium） |
| `tools/patches/` | 开发过程中各轮修改的脚本（仅供参考） |
| `assets/textures/` | 内置 GPT Image 生成的岩层、幕墙、云朵纹理（提示词见 `assets/image-prompts.json`） |
| `assets/web/` | 网页用的 512 px 版本（`tools/make_web_textures.py` 生成，组装时嵌入 `index.html`） |
| `blender/shenzhen-bay.blend` | Blender 4.5 场景（几何取自页面实际生成结果，纹理已打包） |
| `tools/blender/` | 几何导出、场景构建、渲染脚本 |
| `tools/webgl_check.py` | WebGL 冒烟测试与 A/B 帧时间基准 |
| `renders/` | Blender 渲染成品 |
| `CLAUDE.md` | 给 Claude Code 的项目说明、坐标系和下一步计划 |

## 重建

```bash
git clone --depth 1 --filter=blob:none --sparse https://github.com/ni1o1/pygeo-tutorial /tmp/pygeo
git -C /tmp/pygeo sparse-checkout set --no-cone 'shapefile/shenzhen_osmroad.*'
pip install numpy opencv-python pillow
bash tools/build.sh /tmp/pygeo/shapefile
```

只改了页面源码时，直接 `bash tools/build.sh` 即可。替换了 `assets/textures/` 里的纹理后，先运行 `python tools/make_web_textures.py`（需要 Pillow），再执行 `bash tools/build.sh`。

## Blender 场景与渲染

```bash
python3 -m http.server 8765 --bind 127.0.0.1                         # 在项目根目录启动
python tools/blender/export_scene.py                                  # 从页面读回实际几何 → build/blender_export/
blender -b --factory-startup --python tools/blender/build_scene.py    # → blender/shenzhen-bay.blend
blender -b blender/shenzhen-bay.blend --python tools/blender/render.py -- overview city --res 1600x900 --samples 128
```

导出脚本需要 Playwright 和本机 Chrome。场景按“城市 / 岛屿 / 地面与海湾 / 实例 / 云与天空”分集合组织，树、车、路灯、云朵都用几何节点实例化。版本、采样设置、素材用途和测试结果见 `docs/render-notes.md`。

## 测试

```bash
python tools/webgl_check.py http://127.0.0.1:8765/index.html --fallbacks   # 启动、日夜、拾取、窗口尺寸、回退路径
python tools/webgl_check.py <基线URL> <新版URL> --frames 60 --dynres       # A/B 帧时间与动态分辨率重分配
```

## 数据说明

- 道路 © OpenStreetMap 贡献者（ODbL），来自 [ni1o1/pygeo-tutorial](https://github.com/ni1o1/pygeo-tutorial) 中的深圳路网 shapefile。
- 地标坐标与高度来自维基百科。
- 海岸线、绿地由路网推算；其余楼体、球场、停车场、行人、停放车辆为程序生成，不对应真实位置。

## 下一步

Blender 场景已经建好（见上文）。后续可以在其中精细化地标与岛体、烘焙光照后导出 glb，再在页面中加载替换程序生成的版本，详见 `CLAUDE.md`。
