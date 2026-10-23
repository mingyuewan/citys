# 交接：深圳湾 · 空中之岛（2026-10-22）

这份文档写给在本地接手的人，包括你自己和本地的 Claude Code。读完应该知道三件事：项目现在是什么状态、接下来往哪走、第一步具体怎么做。

## 1. 现状

| 部分 | 状态 | 位置 |
| - | - | - |
| 网页（手写 WebGL2，单文件） | 可用。浮空岛、真实路网、11 座地标、约 2,000 栋生成楼体、街道细节、空中元素、昼夜、夜间灯光秀都已完成 | `src/city.src.html` → `index.html` |
| 数据管线 | 可用。OSM 路网 shapefile 生成 `data/szbay.json`，海岸线和绿地由路网推算 | `tools/build_data.py` |
| Blender 场景 | 可用。几何读取自网页实际的 GPU 缓冲，Cycles 渲染的成品已经出过 | `blender/`、`tools/blender/`、`renders/`、`docs/render-notes.md` |
| 演示视频 | 已出 67 秒版本（1280×720，24 帧/秒，软件渲染） | `tools/record.py` |
| 测试 | WebGL 冒烟测试、A/B 帧时间对比、回退路径测试 | `tools/webgl_check.py` |
| 真实建筑数据 | **新加的脚本，还没对线上 Overpass 跑过**（离线 bake 已用样例验证） | `tools/osm/fetch_osm.py` |

数据哪些是真的：道路和 11 座地标的位置、高度是真实的；海岸线和绿地是推算出来的；其余楼体、球场、停车场、行人、停放车辆都是生成的。页面署名里写明了这一点，后续版本要继续保持。

## 2. 方向

参考了 [Zenojz/shibuya-rain-walk](https://github.com/Zenojz/shibuya-rain-walk)。它好看，主要原因不是用了 three.js，而是这四点：**统一的画风**、**真实的建筑数据**、**范围收窄、做深**、**多轮人工挑毛病**。three.js 给的是底层设施：模型加载、动画、后期处理、实例化渲染。我们学它的方法，不复制它的内容。

### 2.1 画风（待你拍板，推荐 A）

- **A. 微缩景观式天空之城（推荐）**：画面像精致的桌面沙盘。颜色干净饱和；楼体有柔和的边缘高光和环境光遮蔽；远景加一点移轴虚化；天空和云偏手绘质感，作为氛围担当。这种风格不要求照片级真实，能藏住生成楼体的“假”，和浮空岛的奇幻设定也天然契合。
- B. 动漫描边风：和 shibuya 接近，辨识度高，但容易被看成模仿它。
- C. 继续走写实：对真实数据和精模的要求最高，6 公里尺度下最难做好。

### 2.2 体验

- **默认模式**：沙盘式鸟瞰浏览（保留现有操作）。
- **新增“飞行”模式**：操控一架小飞行器绕岛、穿瀑布、贴着楼群飞。这是本项目独有的玩法，对应 shibuya 的步行。
- **三个精调的时段预设**，替代连续时间轴：
  - 晨雾：云海最厚，岛半隐半现
  - 黄昏：金色侧光，瀑布反光
  - 夜：灯光秀和孔明灯
- **不做落地步行**，控制范围。

### 2.3 技术

- 渲染层换成 **three.js r160**。three.js 放进仓库的 `vendor/`，用 importmap 引入，运行时不依赖网络。
- **放弃单文件**，改成正常的多文件工程：`src/*.js` 模块，加上 `data/`、`assets/*.glb`。本地起静态服务运行，GitHub Pages 可以直接发布。
- 数据管线、几何生成逻辑和现有着色器的效果尽量复用，不推倒重来。

## 3. 路线图

每个阶段结束都要有一版能直接打开的成品。

### 阶段 1：迁移到 three.js，画面与现在持平

**交付**：`web/` 目录下新的多文件工程（目录结构见第 4 节）。旧的 `src/city.src.html` 保留，作为对照，直到阶段 1 验收。

**验收标准**
- 总览、城市俯瞰、瀑布、岛底、街道、夜景六个视角，和旧版截图并排对比，内容一致，没有缺失。
- 在你的机器上（Radeon Pro 5300M，1280×720），总览视角帧时间中位数不高于旧版。
- `tools/webgl_check.py` 和 `tools/record.py` 改成指向新页面后能跑通，测试钩子见 4.4。
- 拾取、标签、空中漫游、跟随视角、时间滑块和各个按钮的行为不变。

### 阶段 2：定画风，接入真实建筑

1. 运行 `python3 tools/osm/fetch_osm.py fetch`，再运行 `python3 tools/osm/fetch_osm.py bake`，得到 `data/osm/buildings.json` 和 `data/osm/areas.json`。
2. `build_data.py` 改为：
   - 有 OSM 建筑的街区用真实轮廓。
   - 街区里一栋 OSM 建筑都没有时，才用生成楼体补位，并在数据里标记来源。
   - 海岸线改用 `areas.coast`，替换现在由路网推算的海岸。
3. 按选定的画风改材质和后期。
4. 楼群分级细节（LOD）：近处用完整模型，远处合并成简化体块。

**验收**：
- 后海 CBD 和深圳湾公园一带的楼体与卫星图能对上。
- 点开任意一栋楼，能看到它的数据来源（实测高度、层数推算、估算或生成）。
- 帧时间不比阶段 1 差 20% 以上。

### 阶段 3：Blender 精模，以 glb 接入

- **建模对象**：
  - 地标，优先级依次为春笋、春茧、深圳湾一号、腾讯滨海大厦、汉京
  - 浮空岛的岩石本体，带雕刻细节
  - 小物件：树、车、船
- **烘焙**：把环境光遮蔽或光照烘焙进贴图。
- **导出**：glb 格式，Y 轴朝上，单位米，原点按 `CLAUDE.md`。几何用 meshopt 压缩，贴图用 webp，全部资源控制在 15 MB 左右。
- **命名约定**：地标节点名用 `LM_<k>`，`<k>` 取 `data/szbay.json` 中 `landmarks[].k`，例如 `LM_bamboo`、`LM_cocoon`。岛体用 `ISLAND_body`。页面按名字匹配：有对应模型就替换程序生成的版本，没有就保持原样。

### 阶段 4：体验

飞行模式、三个时段预设、音效（可以学 shibuya 用代码实时合成）、页面内录屏（`MediaRecorder`）、开始界面。

## 4. 阶段 1 技术方案

### 4.1 目录

```
web/
  index.html            开始界面 + importmap
  vendor/three/         three.js r160（build/three.module.js 与 examples/jsm 中用到的文件，附 LICENSE）
  src/
    main.js             启动、渲染循环、测试钩子
    world.js            坐标换算、isleR()、hash/rng、几何工具（frustum、各种 ring、triangulate）
    data.js             读取 data/szbay.json 并解码
    island.js           岛体、垂岩、藤蔓、小浮岛、瀑布
    ground.js           地面分类贴图、用地贴图、海水
    roads.js            路面条带、车道线、红绿灯、公交站、路灯
    buildings.js        生成楼体与地标（阶段 3 起优先加载 glb）
    props.js            树、球场、停车、行人
    traffic.js          车流
    air.js              飞机、直升机、飞艇、热气球、白鹭、无人机、灯光秀、孔明灯、探照灯
    sky.js              天空、云海、云团、时段（sky(tod)）
    materials/          各个 ShaderMaterial / onBeforeCompile 注入
    camera.js           轨道镜头、flyTo、视角预设、空中漫游、跟随
    ui.js               标题卡、按钮、信息卡、标签
    post.js             EffectComposer：RenderPass → UnrealBloomPass → OutputPass（ACES）
  data/                 szbay.json（不再内嵌进 HTML）
  assets/               纹理、glb
```

three.js r160 从 npm 的 `three@0.160.1` 里取 `build/three.module.js` 和用到的 `examples/jsm` 文件，MIT 许可。

### 4.2 旧代码对照

旧代码各段以 `src/city.src.html` 中的注释标题为准。

| 旧代码段 | 新位置 | 迁移方式 |
| - | - | - |
| math / floating island outline / geometry builder | `world.js` | 原样搬过去。`Geo` 改成产出 `BufferGeometry`，属性依次为 position、normal、color、uv、bid、mat |
| generated buildings / landmarks / decode data | `buildings.js`、`data.js` | 生成逻辑不变；城市保持一个合并网格，再加地标网格 |
| road surfaces / sports / instanced props / bridges + traffic | `roads.js`、`props.js`、`traffic.js` | 实例化改用 `InstancedMesh` 或 `InstancedBufferGeometry` |
| floating island body / clouds | `island.js`、`sky.js` | 几何不变 |
| aerial actors / dynamic mesh / per-frame aerial update | `air.js` | 灯点改用 `THREE.Points` 加自定义材质；飞机、直升机这些不再每帧重建顶点，改成独立模型加 `Object3D` 变换 |
| scene state / camera / picking | `main.js`、`camera.js` | 拾取改用 `Raycaster` 命中城市网格，再查三角形对应的 `bid` 属性；也可以保留 1×1 GPU 拾取 |
| render targets / shadow / bloom / composite | 删除，改用 three.js 自带功能 | 用 `WebGLRenderer`（`antialias`、`toneMapping: ACESFilmic`）、`DirectionalLight` 阴影和 `post.js`。你那边修好的回退逻辑，three.js 大多已经内置 |
| 着色器 `meshFS` 的材质分支（m 取 0–20） | `materials/building.js` | 一个 `ShaderMaterial`，按顶点上的 `mat` 属性分支，原有分支逻辑照搬。阴影采样改用 three.js 的 shadowmap chunk，也可以先用 `onBeforeCompile` 注入 `MeshStandardMaterial`，把自定义分支逻辑加到 emissive / albedo 上 |
| `roadFS` / `groundFS` / `seaFS` / `fallFS` / `cloudFS` / `skyFS` / `treeFS` / `instFS` | `materials/*.js` | 各写成一个 `ShaderMaterial`；`COMMON` 部分（skyColor、fog、isleR、噪声）做成共享的 GLSL 片段 |

需要特别注意的地方：
- **背面剔除**：旧引擎关闭了背面剔除，在着色器里把背面法线翻过来用。不少三角形是顺时针绕序（Blender 导出脚本已经处理过）。迁移时要么全部设 `side: DoubleSide`，要么在 `Geo` 里统一绕序。推荐统一绕序，能省一半片元开销。
- **`isleR()` 要两边同步**：这个函数同时存在于 JS 和 GLSL 里，改动时两处一起改。最好把参数集中写在 `world.js` 里，再拼进 GLSL。

### 4.3 性能目标

- 城市是一个合并网格，约 12 万个三角形，加上地标。阶段 2 换成真实建筑后预计 3 万到 5 万栋，必须做 LOD 和按区块合并。
- 阴影：一个 `DirectionalLight`，阴影相机跟随镜头的焦点，贴图 2048 或 3072。对静态物体，太阳不动时不必每帧重画阴影（three.js 设 `shadowMap.autoUpdate = false`，需要时手动更新）。
- 在你那台 5300M 上，1280×720 总览视角的目标是 60 帧每秒。

### 4.4 测试钩子（必须保留，录制和测试脚本依赖它们）

- `window.S`（场景状态，包括 `cam`、`tod`、`rise`、`ready`、`osm`）、`setTod`、`flyTo`、`VIEWS`、`HOME`、`startTour`、`stopTour`、`flyToBuilding`、`closeCard`、`setPlate`、`AIR`（`show.t`、`planes` 等）、`FALLS`、`D`、`inIsle`。
- **伪时钟**：渲染循环只能通过 `requestAnimationFrame` 驱动，时间只能通过 `performance.now()` 取得。录制脚本会替换这两个函数来逐帧推进，所以别用 `three.js` 的 `Clock`，或者让 `Clock` 也从 `performance.now()` 取时间。
- **加载完成的标志**：`#loader` 元素加上 `hidden`。Playwright 等待加载时要写 `wait_for_function(..., polling=500)`，因为默认的轮询方式依赖 `requestAnimationFrame`，在伪时钟下会卡死。

## 5. 从 shibuya 学什么、不学什么

**学**：
- 时段做成精调的预设
- OSM 原始数据经 bake 压成场景专用格式（我们的 `tools/osm/` 就是这个思路）
- importmap 加 vendor 目录，运行时不联网
- 页面内录屏
- 声音全部用代码合成
- 先做调研再动手（它的 `docs/research/`）

**不学**：
- 它的人物模型 VRM 限个人非商业使用；Mixamo 动作不能再分发。这些素材一律不用。
- 它的代码是 MIT 许可，可以参考写法，但不要整段复制进来。确实要用的话，保留它的版权声明。

## 6. 环境和踩过的坑

- **坐标系**：见 `CLAUDE.md`。所有资源都必须对齐同一个原点。
- **OSM 数据许可**：ODbL。要保留署名“© OpenStreetMap 贡献者”，再分发数据时也沿用 ODbL。
- **无头浏览器测试**：
  - 有显卡时用 ANGLE（你那边是 Metal）。
  - 没有显卡时用 `--use-gl=angle --use-angle=swiftshader --enable-unsafe-swiftshader`，速度约 3 到 6 秒一帧。
- **Overpass**：主站繁忙时会超时，`fetch_osm.py` 会依次尝试几个镜像。都失败的话，运行 `python3 tools/osm/fetch_osm.py query` 打印出查询语句，到 overpass-turbo.eu 运行，再把结果另存为 `data/osm/raw.json`。
- **数据范围**：现在的数据是以原点为中心 6.4 km 的方形。岛的轮廓半径约 2.85 km，北边有一个伸到汉京中心的小半岛，约 3.4 km。OSM 抓取半径设为 3.5 km。

## 7. 给本地 Claude Code 的第一条指令（可直接粘贴）

```
读 CLAUDE.md 和 docs/handoff.md。按第 4 节，在新分支 threejs-migration 上开始阶段 1：
先搭 web/ 目录、vendor three.js r160、main.js 渲染循环和 world.js/data.js，
把岛体和城市网格用 three.js 画出来，与旧版总览视角截图对比后再继续迁移其他模块。
每完成一个模块就用 tools/webgl_check.py 跑一次截图对比。
```
