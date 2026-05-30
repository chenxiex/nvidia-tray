# nvtray

Linux 托盘程序：检测 NVIDIA PCI 设备并提供“弹出 NVIDIA GPU”菜单项。
[English](README.md)
## 功能

- 自动检测 NVIDIA PCI 设备（厂商 ID: `0x10de`）
- 仅显示显示控制器设备（PCI class 0x03），过滤音频设备
- 仅在检测到 NVIDIA 设备时显示托盘图标
- NVIDIA 设备移除后自动隐藏托盘图标
- 菜单可将 NVIDIA GPU 从 PCI 总线上弹出
- **弹出前自动检测占用目标 GPU 的进程**，如有进程使用则拒绝弹出并显示进程与设备路径
- 支持配置进程白名单：白名单进程占用 GPU 时只在通知中警告，不阻碍弹出
- 默认同时移除同一 PCI slot 下的 NVIDIA 关联 function，例如 HDMI 音频、USB xHCI、UCSI function
- 通过 `pkexec` + `polkit` 获取授权

## 依赖

- Python 3
- `python3-gi`
- `python3-pyudev`
- `gir1.2-ayatanaappindicator3-0.1` 或 `gir1.2-appindicator3-0.1`
- `policykit-1`
- `python3-notify2`
- `gettext`
- Python 构建工具：`build`、`installer`、`setuptools`、`wheel`

Arch Linux 可直接使用 PKGBUILD。

## 安装

构建 wheel 并安装：

```bash
cd /path/to/nvtray
sudo ./install.sh
```

安装后会生成标准 Python 入口：

- `/usr/bin/nvtray`
- `/usr/bin/nvtray-eject-helper`

Arch Linux 可直接使用 PKGBUILD；它会先构建 wheel，再用 `python -m installer` 安装到打包目录。

## 运行

手动运行：

```bash
nvtray
```

启用开机自启动（推荐）：

```bash
systemctl --user enable --now nvtray.service
```

停止并禁用自启动：

```bash
systemctl --user disable --now nvtray.service
```

## Hook 命令

可在以下事件执行自定义 bash 命令：

- `gpu_added`：udev 检测到 NVIDIA 显示控制器后
- `before_eject`：执行 `pkexec nvtray-eject-helper <pci_id>` 前
- `after_eject`：弹出命令结束后（无论成功或失败）

配置文件路径遵循 XDG Base Directory 规范：

- `$XDG_CONFIG_HOME/nvtray/config.json`
- 若未设置 `XDG_CONFIG_HOME`：`~/.config/nvtray/config.json`

旧版本的 INI 配置不再读取。若存在 `config.ini` 但不存在 `config.json`，nvtray 会使用默认配置启动，并显示迁移警告通知。

示例配置：

```json
{
  "hooks": {
    "gpu_added": "/home/user/.local/bin/nvidia-gpu-added.sh",
    "before_eject": "logger -t nvtray \"about to eject $NVTRAY_PCI_ID\" && /home/user/.local/bin/check-safe.sh",
    "after_eject": "[ \"$NVTRAY_EJECT_SUCCESS\" = \"1\" ] && notify-send \"GPU ejected\" \"$NVTRAY_PCI_ID\""
  },
  "eject": {
    "unload_modules": false,
    "wait_seconds": 5,
    "remove_related_functions": true,
    "process_whitelist": [
      "steam",
      {"name": "gamescope", "path": "/dev/dri/renderD*"}
    ]
  }
}
```

每个 Hook 会收到以下环境变量：

- `NVTRAY_EVENT`：`gpu_added`、`before_eject` 或 `after_eject`
- `NVTRAY_PCI_ID`：例如 `0000:01:00.0`
- `NVTRAY_EJECT_SUCCESS`：仅 `after_eject` 有，值为 `1` 或 `0`

说明：

- Hook 配置内容会按 `bash -lc "<你的命令>"` 执行。
- 直接写脚本路径仍然可用，因为脚本路径本身就是合法 bash 命令。
- `before_eject` 为阻塞执行，若返回非 0 则中止弹出。
- `gpu_added` 和 `after_eject` 为异步执行。

弹出选项：

- `unload_modules`：设为 `true` 时，helper 会在移除 PCI 设备后尝试卸载 NVIDIA 内核模块。默认禁用，仅建议作为最后手段或调试选项，因为卸载模块可能影响其它 NVIDIA GPU，也可能影响 Vulkan/Wine/DXVK 用户态状态。
- `wait_seconds`：移除后等待 PCI function 和 DRM 节点消失的秒数。默认值：`5`。
- `remove_related_functions`：设为 `true` 时，helper 会移除所选显示控制器同一 slot 下的所有 NVIDIA PCI function。默认值：`true`。
- `process_whitelist`：允许占用 GPU 但不阻碍弹出的进程/路径模式 JSON 数组。字符串项如 `"steam"` 会视为 `"steam=*"`，表示该进程可占用任意被检测到的 GPU 路径；对象项如 `{"name": "gamescope", "path": "/dev/dri/renderD*"}` 更严格，仅允许匹配的进程/路径组合。`name` 和 `path` 都支持 `*`、`?` 等 shell 风格通配符。

## 说明

- helper 只允许处理格式正确的 PCI ID，并校验设备厂商必须是 NVIDIA。
- **弹出前会检查是否有进程正在使用 GPU**：
  - 扫描进程文件描述符，检查目标卡对应的 `/dev/dri/card*`、`/dev/dri/renderD*` 和 DRM sysfs 节点
  - 仅当 `eject.unload_modules = true` 时，额外检查 `/dev/nvidiactl` 等 NVIDIA 驱动节点
  - 如检测到进程占用，将拒绝弹出并显示进程名称、PID 和设备路径
  - 若占用进程匹配 `eject.process_whitelist`，则不阻碍弹出。未指定路径的项会视为 `path=*`；更严格的项只允许匹配的进程/路径组合。允许项会在通知中警告
- **弹出流程**：
  - 弹出前将所选显示控制器的 runtime power control 设为 `on`
  - 先移除同一 slot 下的 NVIDIA 关联 function，再移除显示控制器
  - 等待 PCI function 和 DRM 节点消失后才报告成功
  - 仅当 `eject.unload_modules = true` 时尝试卸载 NVIDIA 内核模块（nvidia_uvm, nvidia_drm, nvidia_modeset, nvidia）
- 默认 polkit 策略为管理员认证（活跃会话可缓存认证）。
