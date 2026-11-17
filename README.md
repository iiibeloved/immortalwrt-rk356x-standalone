# ImmortalWrt · 农商云 G68-PLUS（RK3568）定制固件

[![构建状态](https://github.com/iiibeloved/immortalwrt-rk356x-standalone/actions/workflows/build-g68-plus-docker.yml/badge.svg)](https://github.com/iiibeloved/immortalwrt-rk356x-standalone/actions/workflows/build-g68-plus-docker.yml)
[![最新 Release](https://img.shields.io/github/v/release/iiibeloved/immortalwrt-rk356x-standalone)](https://github.com/iiibeloved/immortalwrt-rk356x-standalone/releases/latest)

> 一句话简介：给 **农商云 NSY G68-PLUS（RK3568）** 用的 ImmortalWrt 24.10 定制固件，iStoreOS 风格（商店 + 向导）、Docker / DDNS / 文件共享 / 分区工具齐全，并且**不做任何自动分区或格式化**，把有断电风险的磁盘操作完全交给你自己决定。

如果你是第一次接触本固件，建议只看下面四节即可完成刷机：**[固件特点](#二固件特点) → [刷机前注意事项](#四刷机前注意事项) → [刷机方法](#五刷机方法) → [刷机后注意事项](#六刷机后注意事项)**。其余章节是进阶说明。

> 致谢：本仓库 fork 自 [@zhoufuli](https://github.com/zhoufuli/immortalwrt-rk356x)，设备适配（DTS / u-boot / 分区）全部来自上游；感谢 [ImmortalWrt](https://github.com/immortalwrt)、[OpenWrt](https://openwrt.org)、[kenzok8/small-package](https://github.com/kenzok8/small-package)、[iStoreOS](https://github.com/linkease)、[sirpdboy](https://github.com/sirpdboy) 等项目的软件包与源。

---

## 目录

- [一、这是什么](#一这是什么)
- [二、固件特点](#二固件特点)
- [三、包含内容](#三包含内容)
- [四、刷机前注意事项](#四刷机前注意事项)
- [五、刷机方法](#五刷机方法)
- [六、刷机后注意事项](#六刷机后注意事项)
- [七、下载与校验](#七下载与校验)
- [八、已知限制](#八已知限制)
- [九、常见问题](#九常见问题)
- [十、技术实现（进阶）](#十技术实现进阶)
- [十一、本地构建](#十一本地构建)
- [致谢 / 文档](#致谢--文档)

---

## 一、这是什么

本固件面向 **RK3568 架构的 G68-PLUS 软路由 / NAS 小板**，在 ImmortalWrt 24.10 上叠加 iStoreOS 风格的应用生态，并坚持一个原则：**固件只负责系统本身，磁盘的数据分区由你手动规划**。

| 组成 | 来源 | 带来的好处 |
| --- | --- | --- |
| **系统基座** | [ImmortalWrt 24.10](https://github.com/immortalwrt/immortalwrt) + [OpenWrt](https://openwrt.org) | 内核 6.6、官方软件源、稳定的底层网络栈 |
| **设备适配层** | fork 自 [@zhoufuli/immortalwrt-rk356x](https://github.com/zhoufuli/immortalwrt-rk356x) 的 DTS / u-boot / 分区 | 长按 Reset 进 MaskROM、5 口千兆、eMMC 布局 |
| **应用生态** | iStore 商店、quickstart 向导、small-package、sirpdboy、lucky 等 | 商店、Docker、DDNS、共享、分区工具一应俱全 |

它提供**两个变体**，发布在**同一个 Release**（generic 资产名带 `-generic`）：

| 变体 | 定位 |
| --- | --- |
| **full**（默认） | 带内置初始化脚本 / 自动配置；首次启动会自动运行脚本并重启一次（见[刷机后注意事项](#六刷机后注意事项)） |
| **generic** | 纯应用 + 全手动配置，不含上述自动脚本，适合想完全自己掌控的用户 |

> 想要基于 **iStoreOS 官方基座**、采用 swconfig 或 DSA 网络栈的版本，请看姊妹仓库 [istoreos-hybrid-g68](https://github.com/iiibeloved/istoreos-hybrid-g68) 与 [istoreos-hybrid-g68-dsa](https://github.com/iiibeloved/istoreos-hybrid-g68-dsa)。

---

## 二、固件特点

- **不碰你的数据盘。** 不自动分区、不自动格式化、不因磁盘操作而自动重启；只自动**挂载**已有文件系统（如 NVMe）。有断电风险的划盘 / 格式化一律由你手动执行。
- **iStoreOS 风格，开箱即用。** `luci-app-store`（iStore 商城）+ `luci-app-quickstart`（初始化向导），商店、Docker、DDNS、共享、分区工具齐全，不是精简固件。
- **Docker 就绪，日志不撑爆盘。** `dockerd/containerd/runc` + `luci-app-dockerman`；数据目录可指到 NVMe/eMMC，容器日志按 uci 自动轮转（10 MiB × 3）。
- **分区工具齐全。** `parted / fdisk / cfdisk / cgdisk / gdisk / sfdisk` + `luci-app-partexp`（界面化格式化 / 扩容 / 挂载）。
- **软件源开箱可用。** 官方源 + iStoreOS 源；`/etc/opkg.conf` 架构表内置、签名校验默认注释（避免 iStoreOS 源报错）。
- **运维友好。** `firstboot-status` 一键自检；LAN 默认 `192.168.100.1`；TTYD 改 IP 不掉线。
- **配置可复现。** 冻结基线 + CI 指纹校验，配置被改动会在构建时拦下；每周定时重建，上游更新自动带入。

---

## 三、包含内容

### 3.1 主要软件

| 类别 | 代表组件 |
| --- | --- |
| 商店 / 向导 | `luci-app-store`（iStore 商城）、`luci-app-quickstart`、`taskd`、`luci-lib-taskd` |
| 容器 | `dockerd`、`containerd`、`runc`、`luci-app-dockerman` |
| 共享 / 存储 | `samba4`、`unishare`、`luci-app-nfs`、`luci-app-cifs-mount`、`luci-app-diskman`（SMART） |
| 分区 | `luci-app-partexp`、`parted`、`fdisk`、`cfdisk`、`cgdisk`、`gdisk`、`sfdisk` |
| DDNS | `luci-app-ddns`（+ 中文）、`ddns-scripts`、`ddns-go`、`luci-app-ddns-go` |
| 监控 / 管控 | `luci-app-nlbwmon`、`luci-app-rtbwmon`、`luci-app-eqosplus`、`luci-app-timecontrol`、网站/URL 过滤 |
| 代理 | `shadowsocks-rust`、`xray-core`、`v2ray-plugin`、`chinadns-ng`、`lucky` |
| 文件 / 应用 | `luci-app-filemanager`、`luci-app-filetransfer`、`luci-app-homeassistant`（Docker 方式，含中文） |

> 完整且权威的清单见 [docs/packages.md](docs/packages.md)（基线 + 指纹）；当前构建配置约 **599** 项。仓库会持续更新，本文不写死完整清单。

### 3.2 网口与默认网络

- 默认 **LAN `192.168.100.1`**、root 用户、**空密码**（首次登录请立刻设置）。
- WAN 默认 DHCP 客户端，接上级路由 / 光猫即可上网。
- 厂商固件默认是 `192.168.1.1` / `root` / `password`；**本固件不同**，刷机前请留意。
- RJ45 网口灯由 RTL8367S 硬件驱动，软件不可控（属正常现象）。

### 3.3 分区布局

| 分区 | 大小 | 用途 |
| --- | --- | --- |
| `uboot` / SPL | 预编归档 | 由 RKDevTool 写入；`uboot.config` 可在设备内 `cat /etc/uboot.config` 查询 |
| `kernel` | 16 MiB（构建可配） | 内核 + DTB（FIT 镜像） |
| `rootfs` | 200 MiB（默认，构建可配） | 只读 squashfs 系统 |
| `rootfs_data` | 自动创建 | 可写 overlay（配置、opkg、Docker 默认目录所在） |
| 数据盘 | 由你手动规划 | NVMe / eMMC 剩余空间需自行分区、格式化、挂载（见[刷机后注意事项](#六刷机后注意事项)） |

> 镜像为 `*-sysupgrade.img.gz`，刷机前需解压成 `.img`；`rootfs_data` 文件系统在首次启动时创建。完整分区与迁移约定见 [docs/invariants.md](docs/invariants.md)。

---

## 四、刷机前注意事项

1. **准备工具**：双公头 USB 数据线、`RKDevTool_Release_v3.18`、驱动 `Rockchip_DriverAssitant_v5.12`，以及**解压成 `.img` 的固件**（刷机工具不认 `.img.gz`）。
2. **核对文件**：下载后用 `sha256sum -c sha256sums` 校验镜像，不一致请重新下载。
3. **备份配置**：旧系统还能进入时，先在 LuCI「系统 → 备份/升级」导出配置备份。
4. **确认机型**：本固件适用于带 USB 口、可 MaskROM 刷写的 **农商云 G68_PLUS / 彼度云 G18_PRO / G18_PLUS**；**G16_PLUS 无 USB 口，不适用**。
5. **理清地址/密码差异**：厂商默认 `192.168.1.1` / `root` / `password`；**本固件是 `192.168.100.1` / `root` / 空密码**。
6. **保证供电**：刷写与首次启动期间**不要断电**，eMMC 写入中断最难恢复。
7. **SPI flash**：板上若有 SPI flash，建议先清 SPI 再刷 eMMC（见刷机方法）。

---

## 五、刷机方法

系统能否进入，选择对应方式：

### 5.1 系统还能进 → 在线升级

```
LuCI → 系统 → 备份/升级 → 上传 .img.gz → 勾选「保留配置」→ 执行
```

### 5.2 首次刷写 / 进不去系统 → USB 刷机（MaskROM）

> 依据厂商《农商云&彼度云刷固件教程》：**必须用 USB 接口刷**，适用于带 USB 口的农商云 G68_PLUS、彼度云 G18_PRO / G18_PLUS（G16_PLUS 无 USB 口不适用）。

1. 电脑安装驱动 `Rockchip_DriverAssitant_v5.12`，打开 `RKDevTool_Release_v3.18`。
2. **进 MaskROM（两种任选）**：
   - 拆掉 / 短接 SPI 后：双公头线插板子 USB 口 → 短接板上两个短接点 → 通电；
   - **不拆 SPI、不短接也可以**：断电 → **按住 Reset 不松开** → 同时插电源 → 直到刷机软件「发现设备」→ 在「高级功能」里点 **进入 maskrom**（没提示通常是驱动没装好）。
3. 切到 **高级功能** → 导入 `rk356x_spl_loader_v1.21.113.bin` → **下载 uboot**（右侧提示成功）。
4. **获取当前存储**：显示 **SPI** 就点 **擦除所有** 清空 SPI；没有 SPI / 已切到 **EMMC** 同样点 **擦除所有**；进度到 **100%** 才算成功（若“秒擦除”，说明 eMMC 可能有问题，需要检查）。
5. 点工具栏第一个页签 **下载镜像**：表格每行对应一个分区 / 组件，只需关注**有路径的那一行**（通常是 `System`，路径指向你解压的 `.img`）；若路径为空，点该行右侧 `...` 选择 `.img`，并勾上该行左侧复选框。
6. **「强制按地址写」复选框一定要打勾**（位于窗口左下角、`执行` 按钮下方），否则可能写入不完整 / 校验失败；点 **`执行`**，等进度到 100% 并提示成功。
7. 完成后**断电重启**（或断开 USB 再上电），接网线，**网口灯亮**即表示已启动。

> 完整图文步骤见 [docs/build-guide.md](docs/build-guide.md) 4.5 节。

---

## 六、刷机后注意事项

> **本节是新旧版本差异最容易被忽略的地方，请按序号操作。**

> ⚠️ **首次刷机后请勿着急——full 版需要等待约 5～8 分钟。** full 版首次启动会自动运行内置脚本（初始化 uci-defaults、服务编排、LAN 地址设置等），脚本执行完毕后会**自动重启一次**完成初始化。期间管理页面打不开、网口灯闪烁、看似"没反应"均属正常，**不是固件故障**。请耐心等待 5～8 分钟、待自动重启完成后再开始下面的配置；期间**不要断电、不要反复重启、不要急于判定刷机失败**。generic 版不含这些脚本，无此等待过程。

1. **登录并改密码（第一步）。** 浏览器访问 `http://192.168.100.1` → 系统 → 管理权 → 修改密码（默认是空密码，必须第一时间设置）：

   ```sh
   passwd root
   uci set system.@system[0].timezone='CST-8'; uci set system.@system[0].zonename='Asia/Shanghai'
   uci commit system
   ```

2. **确认上网。** WAN 接上级路由 LAN（默认 DHCP），验证 LAN / DHCP / 外网与软件源：

   ```sh
   ping -c3 223.5.5.5 && opkg update
   ```

3. **磁盘（可选，按需）。** NVMe 有文件系统会自动挂到 `/mnt/nvme0`；空白盘 / 要改分区请手动规划：

   ```sh
   # 方式A：界面  系统 → 挂载点（或 系统 → Partition Expansion）
   # 方式B：命令行（eMMC 划 ext_relay + Data；下面数值仅为示例，请按实际容量调整）
   parted -s /dev/mmcblk0 unit MiB mkpart extended 4598 100%
   parted -s /dev/mmcblk0 unit MiB mkpart logical ext4 4599 55798
   parted -s /dev/mmcblk0 unit MiB mkpart logical ext4 55799 100%
   reboot                                    # 必须！内核才认新分区
   mkfs.ext4 -F -m 0 -L ext_relay /dev/mmcblk0p5
   mkfs.ext4 -F -m 0 -L Data      /dev/mmcblk0p6
   mkdir -p /mnt/ext_relay /mnt/data
   mount -t ext4 /dev/mmcblk0p5 /mnt/ext_relay
   mount -t ext4 /dev/mmcblk0p6 /mnt/data
   block detect > /etc/config/fstab && uci commit fstab
   ```

4. **Docker 数据目录（默认 `/opt/docker` 在 4 GiB overlay，必须改）。**

   ```sh
   uci set dockerd.globals.data_root='/mnt/nvme0/docker'   # 或 /mnt/ext_relay/docker
   uci commit dockerd && /etc/init.d/dockerd restart
   docker info | grep -i 'docker root dir'
   ```

5. **iStore 安装位置。** iStore → 安装弹窗「存储位置」选已挂载的盘（如 `/mnt/nvme0`）；程序本体固定进 `/overlay`，装前看 `df -h /overlay`。
6. **收尾。** `firstboot-status` 全绿 → 系统 → 备份/升级 → 生成配置备份并妥善保存。

> 完整分步（含每个 LuCI 菜单路径）见 [docs/first-boot-checklist.md](docs/first-boot-checklist.md)。

---

## 七、下载与校验

- **最新 Release**：<https://github.com/iiibeloved/immortalwrt-rk356x-standalone/releases/latest>
- 版本号、镜像与校验值**以 Release 页面为准**（本仓库持续更新，本文不写死过期版本号与哈希）。

| 资产 | 说明 |
| --- | --- |
| `immortalwrt-rockchip-armv8-nsy_g68-plus-squashfs-sysupgrade.img.gz` | **full** 固件镜像（约 168.6 MiB，刷机前解压） |
| `immortalwrt-rockchip-armv8-nsy_g68-plus-squashfs-sysupgrade-generic.img.gz` | **generic** 固件镜像（约 168.6 MiB） |
| `sha256sums` | 镜像校验值 |
| `uboot.config` | 预编 u-boot 配置，供设备内查询 |

**国内加速**（把 `<tag>` 和 `<file>` 替换为实际版本号与文件名，`https://` 后拼接以下前缀，sha256 不变）：

- `https://gh-proxy.com/https://github.com/iiibeloved/immortalwrt-rk356x-standalone/releases/download/<tag>/<file>`
- `https://ghfast.top/https://github.com/iiibeloved/immortalwrt-rk356x-standalone/releases/download/<tag>/<file>`
- `https://ghproxy.net/https://github.com/iiibeloved/immortalwrt-rk356x-standalone/releases/download/<tag>/<file>`

---

## 八、已知限制

- **不做自动分区 / 格式化**：已移除（断电风险）；数据盘请手动规划，见 [docs/invariants.md](docs/invariants.md)。
- **`mergerfs` 未集成**：OpenWrt 24.10 无此包。
- **RJ45 网口灯不可控**：由 RTL8367S 硬件驱动，软件无法修改。
- **内核模块与自编内核绑定**：**不能**用官方 kmods 源安装，需随固件重编。
- **GitHub cron 偶有延迟 / 跳过**：已用脚本核验兜底。
- **full / generic 差异与内置项**：见 [docs/builtin-list.md](docs/builtin-list.md)。

---

## 九、常见问题

| 现象 | 处理 |
| --- | --- |
| `opkg` 报 `has no valid architecture` | 架构表坏了：`sed -i '/^arch/d' /etc/opkg.conf` 后补 `all/noarch/aarch64_generic/aarch64_cortex-a53` 四行 |
| iStoreOS 源 `Signature check failed` | 固件默认已注释 `option check_signature`；旧版手动注释即可 |
| `mkfs` 报 `No such device` | 新建分区后**必须重启**，内核才认新分区 |
| Docker 日志占满盘 | 固件已增强 init，按 uci 自动轮转（10 MiB × 3），无需手工 |
| Docker 只有 `vfs`、空间暴涨 | `data_root` 在 overlay 上；改到真实 ext4 挂载点（如 `/mnt/nvme0/docker`）后重启 dockerd |
| HA 安装报 `registry-1.docker.io` 超时 | 固件已内置镜像加速；手动兜底见 [docs/build-guide.md](docs/build-guide.md) K4.7 |
| 拉镜像报 `not in the allowlist` / `503` | 镜像站策略，换 `docker.1panel.live` 前缀拉取再 retag，见 K4.9 |
| 报 `registry.linkease.net:5443 ... connection refused` | 那是本机 **KSpeeder（iStore 增强）** 端点未启动；`/etc/init.d/istoreenhance restart` 即可，见 K4.10 |
| HA 没有 HACS | HA ≥ 2026.11 用内置 **Marketplace** 取代 HACS |
| 刷机后管理页打不开 | full 版首启需 5～8 分钟并自动重启一次，请耐心等待；generic 版无此过程 |

---

## 十、技术实现（进阶）

### 10.1 构建与发布

- **自动构建**：GitHub Actions 每周六 **02:00 CST**定时构建，也可在 Actions 手动触发（可改 defconfig / 附加配置 / rootfs 大小）。
- **两个变体**：full 构建成功后自动追加触发 generic 追编，两者发布在**同一个 Release**。
- **产物**：`*.img.gz` + `sha256sums` + `uboot.config`，免登录直链发布到 Release。
- **配置可复现**：冻结基线 + CI 指纹校验（改动会被拦下），上游 feeds / 插件更新在下一次定时构建中自动带入。

### 10.2 关键机制

- **长按 Reset → MaskROM**：沿用上游设备的按键链路，断电按住 Reset 上电可被 RKDevTool 识别（也支持短接测试点兜底），u-boot 预编并归档 `.config`。
- **零自动磁盘操作**：不因磁盘操作自动分区 / 格式化 / 重启；只自动挂载已有文件系统，把数据安全交给你。
- **full / generic 裁剪**：构建时按 variant 裁剪内置脚本 / 配置——full 带初始化脚本（首启自动配置并重启一次），generic 为纯应用手动配置。
- **分区表校验**：构建过程校验镜像分区布局，避免写出不可用的整盘镜像。

### 10.3 构建流水线

```text
触发（schedule 周六 02:00 CST / push defconfig / workflow_dispatch / repository_dispatch）
   │
   ▼
build（单一主作业，顺序执行）
   检出源码 → 单元测试(发布逻辑) → 校验配置与目标
   ▼
安装依赖 → 生成 feeds.conf（官方源）→ 更新并安装官方 feeds
   ▼
引入第三方 feed（选择性安装）+ 本地单包（filetransfer / partexp / menusort）
   ▼
写入构建信息 /etc/g68-build → 按 variant 裁剪内置脚本（full / generic）
   ▼
应用 defconfig + 附加配置 + rootfs 大小 → make defconfig → make prereq → 校验附加包
   ▼
缓存 dl / ccache → 下载源码 → 构建工具链 → 预编 u-boot 并归档 .config
   ▼
编译固件 → 记录 rootfs 占用 → 校验镜像分区表 → 收集固件
   ▼
上传 artifact → 发布到 Release（免登录直链）→ full 成功后自动触发 generic 追编
   ▼
构建失败自动开 issue（同类复用）/ 成功自动关闭失败 issue
```

| 环节 | 职责 |
| --- | --- |
| 触发 | `schedule`（每周六 02:00 CST）、`push`（defconfig / workflow 变更）、`workflow_dispatch`（可改配置 / rootfs 大小）、`repository_dispatch` |
| `build` | 单一主作业：feeds 与第三方包、variant 裁剪、配置归一化与校验、工具链、u-boot 预编、全量编译、镜像分区表校验、发布 Release |
| `publish-release.yml` | 独立发布作业（仅手动 / API 触发）：下载构建产物 → 解出固件与校验文件 → 复用 `release-append-lib` 上传到 Release |
| variant 追编 | full 成功后自动触发 generic 追编，两变体发布在同一个 Release |
| issue 联动 | 构建失败自动开 issue（同类复用不重复），成功时自动关闭失败 issue |

触发方式：`schedule`（每周定时）、`push`（配置变更）、`workflow_dispatch`（手动）、`repository_dispatch`（外部触发）；发布另有独立的 `publish-release.yml`。

### 10.4 仓库结构

```text
defconfig/                g68-plus-docker.config（基础）+ g68-plus-istoreos.config（附加）
files/etc/                品牌、i18n、ttyd、g68 内置脚本与 init.d
docs/                     build-guide / first-boot-checklist / packages / invariants / builtin-list
docs/scripts/             bootstrap-remote.sh / setup-router.sh / docker-apps.sh
.github/workflows/        build-g68-plus-docker.yml（构建）/ publish-release.yml（发布）
config/                   OpenWrt 构建配置框架
```

### 10.5 不变量（任何改动都不得破坏）

1. 设备适配以 fork 上游基线为准，品牌 / 网络 / 按键能力不回退；
2. 不做自动分区 / 格式化，不因磁盘操作自动重启；
3. 默认 LAN `192.168.100.1`、root 空密码（首启提示改密）；
4. 配置基线 + 指纹校验，构建可复现；
5. full / generic 同 Release 发布，差异在 `docs/builtin-list.md` 记录。

---

## 十一、本地构建

```sh
git clone https://github.com/iiibeloved/immortalwrt-rk356x-standalone.git
cd immortalwrt-rk356x-standalone
cp defconfig/g68-plus-docker.config .config
# 如需 iStoreOS 风格附加配置，合并 defconfig/g68-plus-istoreos.config
cat defconfig/g68-plus-istoreos.config >> .config
make defconfig && make -j"$(nproc)"
```

产物：`bin/targets/rockchip/armv8/*nsy_g68-plus*sysupgrade.img.gz`

> 省事做法：直接在 Actions 页面「Run workflow」手动触发，可在线调整 defconfig / rootfs 大小并自动发布到 Release。

---

## 致谢 / 文档

- [iStoreOS](https://github.com/istoreos/istoreos) / [ImmortalWrt](https://github.com/immortalwrt/immortalwrt) / [OpenWrt](https://openwrt.org) —— 系统基座与软件生态
- [@zhoufuli/immortalwrt-rk356x](https://github.com/zhoufuli/immortalwrt-rk356x) —— 设备适配（DTS / u-boot / 分区）上游
- [docs/build-guide.md](docs/build-guide.md) —— 构建 / 刷机 / 维护全教程（含 USB maskrom、dd、手动分区、附录）
- [docs/first-boot-checklist.md](docs/first-boot-checklist.md) —— 刷机后完整操作流程
- [docs/packages.md](docs/packages.md) —— 固件包清单（基线 + 指纹）
- [docs/invariants.md](docs/invariants.md) —— 部署约定与迁移手册（换盘 / 重刷后怎么恢复）
- [docs/scripts/](docs/scripts/) —— 内置运维脚本

> 本仓库仅做设备层移植与 CI 编排，固件内容遵循各上游组件许可证。
