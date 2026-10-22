我只读了 `src/city.src.html` 中 WebGL 相关的部分（1032–1101、1397、1797–1830、2420–2463、2762–2790、2998–3297 行），没有修改任何文件。下面是证据最充分的 3 个问题，按影响排序。

## 1. 动态分辨率每次调整都会重建所有 render target，造成周期性卡顿和显存反复分配

**证据**
- `src/city.src.html:3036-3040`：每 2 秒按 `PERF.scale *= 0.85` 或 `*= 1.08` 调整一次缩放。这两个系数不是互逆的，帧时间在阈值附近时会来回切换，算出的尺寸几乎每次都不一样。
- `src/city.src.html:3004-3007`：`resize()` 把 `PERF.scale` 直接乘进 dpr，再四舍五入得到像素尺寸，所以每次缩放调整都会改变尺寸。随后每帧都调用 `setupRT(w, h)`。
- `src/city.src.html:2431-2447`：只要尺寸变了，就删除并重建 4x MSAA 的 RGBA16F 颜色缓冲、DEPTH24 深度缓冲、全分辨率场景纹理，以及 5 级 bloom 纹理。按 3.2M 像素的上限估算，单次重建约 180MB。
- `src/city.src.html:2767-2777`：拾取用的 FBO 也是全分辨率（RGBA8 加深度），尺寸一变，下次点击就要重建。接着 `2786` 行用同步的 `readPixels` 读回，会造成 GPU 阻塞。
- `resize()` 每帧都读取 `clientWidth`，而上一帧末尾（`3287-3288` 行）刚写过大量标签的 `transform`，这会触发样式重算。

**修复建议**
- 把缩放改成固定档位（如 `[1, 0.85, 0.7, 0.6]`），升档和降档用不同阈值，并且至少间隔 5 秒以上才允许再次调整。
- render target 只在需要变大时重新分配，并按 64px 对齐。缩小时保留原纹理，通过 `viewport` 只渲染一个子区域，composite 时用 UV 缩放。
- 只在 `ResizeObserver` 回调里读取 CSS 尺寸。
- 拾取改为 1×1 的 scissor 渲染，或者对屏幕尺寸的 FBO 只在点击时临时 `scissor` 到点击位置。

## 2. 浮点 MSAA FBO 没有检查格式能力和完整性，部分 GPU 上可能直接黑屏，且无法恢复

**证据**
- `src/city.src.html:1037`：只要拿到 `EXT_color_buffer_float` 就把 `floatRT` 设为 true，并在 `2438` 行把 MSAA 颜色格式定为 RGBA16F。
- `src/city.src.html:2439`：采样数用的是 `gl.MAX_SAMPLES`，这是全局最大值，不是 RGBA16F 这个格式支持的采样数。部分 Android 和较旧的 iOS 设备上，RGBA16F 多重采样支持的采样数更少，甚至不支持。
- 整个 `setupRT` 和 `mkTex` 都没有调用 `gl.checkFramebufferStatus`，出错时没有回退路径。FBO 不完整时，`3146` 行的绘制和 `3247` 行的 `blitFramebuffer` 会静默失败，最终输出黑屏。
- 全文没有 `webglcontextlost` 或 `webglcontextrestored` 处理。这个页面显存占用很高（MSAA、3072² 的阴影贴图、4096² 的地面纹理加 mipmap），在移动端切到后台后很容易丢失 context，之后不会恢复。

**修复建议**
- 采样数用 `gl.getInternalformatParameter(gl.RENDERBUFFER, fmtC, gl.SAMPLES)` 查询，取 `min(4, 其中最大值)`。
- 每个 FBO 创建后都检查完整性。失败时按顺序回退：RGBA16F MSAA → RGBA8 MSAA → 不用 MSAA，直接用纹理 FBO。
- 监听 `webglcontextlost`（调用 `preventDefault`，并停止 `tick`）和 `webglcontextrestored`（重新执行 `compile`、`setupRT`、阴影贴图初始化和 `buildScene` 里的上传），或者至少给出“请刷新”的提示。

## 3. 阴影开销过高：分辨率写死、每帧全量重绘、PCF 采样过多

**证据**
- `src/city.src.html:2451-2453`：第一行按 `MAX_TEXTURE_SIZE` 算出的上限，紧接着被 `SM.size = 3072` 覆盖，那段计算等于没用。WebGL2 只保证 2048，3072² 的 DEPTH24 约占 36MB，低端设备上可能分配失败，或者占满显存带宽。
- `src/city.src.html:3114-3136`：只要是白天，每帧都把整座城市（`S.city.count`）、岛体、所有树的实例、车和路灯重新画进阴影贴图，没有视锥剔除。即使太阳和镜头都没动，也照样重画。动态分辨率（问题 1）只缩小主画面，阴影这部分开销不会跟着降。
- `src/city.src.html:1097`：`shadowAt` 做 3×3 共 9 次 `texture(sampler2DShadow)` 采样，而阴影纹理设置的是 `LINEAR` 比较过滤（`2456` 行），硬件每次已经做了 2×2 PCF，相当于每个片元约 36 次 texel 读取。这个函数被 mesh、road、inst、tree、ground 等所有主要着色器调用，在高 overdraw 的楼群区域开销很大。

**修复建议**
- 删掉 `2453` 行的写死值，改成 `min(MAX_TEXTURE_SIZE, 档位)`。移动端或 `PERF.scale < 1` 时降到 2048。
- 缓存静态阴影：只在 `focus` 吸附到新的 texel、`lightDir` 变化超过阈值或 `S.rise < 1` 时重画城市和岛的阴影。动态物体（车、飞机）的阴影可以分开降频画，或者干脆不投影。
- 既然已经有硬件 2×2 PCF，可以把 3×3 改成 4 个 tap 的旋转 Poisson 采样或 2×2 偏移采样，采样量减少约一半，视觉差异很小。

---

另外有两点影响较小：bloom 链的第一级是半分辨率的 RGBA16F，再加上亮度提取要读取全分辨率场景，这部分开销不大；`3125`/`3140` 行每帧用 `bufferSubData` 上传 DYN 和实例数据，属于正常用法。所以都没有列入前三。

如需按上面的建议修改，请告诉我从哪一项开始。
