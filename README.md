# nvidia-tray

Linux 托盘程序：检测 NVIDIA PCI 设备并提供“弹出 NVIDIA GPU”菜单项。

## 功能

- 自动检测 NVIDIA PCI 设备（厂商 ID: `0x10de`）
- 仅显示显示控制器设备（PCI class 0x03），过滤音频设备
- 仅在检测到 NVIDIA 设备时显示托盘图标
- NVIDIA 设备移除后自动隐藏托盘图标
- 菜单可对单个 PCI 设备执行弹出（`unbind` + `remove`）
- **弹出前自动检测占用 GPU 的进程**，如有进程使用则拒绝弹出并显示进程列表
- 通过 `pkexec` + `polkit` 获取授权

## 依赖

- Python 3
- `python3-gi`
- `python3-pyudev`
- `gir1.2-ayatanaappindicator3-0.1` 或 `gir1.2-appindicator3-0.1`
- `policykit-1`
- `python3-notify2`

Debian/Ubuntu 可参考：

```bash
sudo apt install -y python3-gi python3-pyudev gir1.2-ayatanaappindicator3-0.1 policykit-1
```

## 安装

```bash
cd /path/to/nvidia-tray
sudo ./install.sh
```

## 运行

手动运行：

```bash
nvidia-tray
```

启用开机自启动（推荐）：

```bash
systemctl --user enable --now nvidia-tray.service
```

停止并禁用自启动：

```bash
systemctl --user disable --now nvidia-tray.service
```

## 说明

- helper 只允许处理格式正确的 PCI ID，并校验设备厂商必须是 NVIDIA。
- **弹出前会检查是否有进程正在使用 GPU**：
  - 使用 `fuser` 检测打开 `/dev/nvidia*` 设备的进程
  - 如检测到进程占用，将拒绝弹出并显示进程名称和 PID
- **弹出流程**：
  - 直接写入 PCI 设备的 `remove` 接口移除设备
  - 尝试卸载 NVIDIA 内核模块（nvidia_uvm, nvidia_drm, nvidia_modeset, nvidia）
- 默认 polkit 策略为管理员认证（活跃会话可缓存认证）。
