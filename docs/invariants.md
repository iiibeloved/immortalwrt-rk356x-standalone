# 部署约定与迁移手册（Invariants）

> 这里列出**必须保持不变**的路径、名字与配置键。改它们会同时影响固件内置脚本、
> uci-defaults、Docker 与 iStore 的既有配置；换盘 / 重刷后也按本文恢复。
>
> 仅 **full 变体**包含下列脚本与约定；**generic 变体**不固化任何脚本（只保留软件源配置），
> 所有路径都需手动配置。

---

## 1. 分区与文件系统

| 分区 | 大小 | 文件系统 | 说明 |
| --- | --- | --- | --- |
| p1 kernel/boot | 16 MiB | 原始分区 | 内核 + dtb，勿动 |
| p2 rootfs | `rootfs_size`（默认 200 MiB） | squashfs（只读） | 系统本体 |
| p3 rootfs_data | `rootfs_data_size`（默认 4096 MiB） | ext4 | overlay：配置、opkg 装包、iStore 程序本体 |
| p5（手动） | 自定 | ext4，标签 `ext_relay` | Docker 数据盘 |
| p6（手动） | 自定 | ext4，标签 `Data` | 共享数据盘 |

- 分区表校验写死在 CI（`校验镜像分区表` 步骤），改动大小需同步改工作流输入默认值。
- `rootfs_data` 大小由 `ROOTFS_DATA_PARTSIZE` 环境变量传给 [scripts/gen_image_generic.sh](../scripts/gen_image_generic.sh)。

## 2. 挂载点（名字不可改）

| 挂载点 | 用途 | 谁在用 |
| --- | --- | --- |
| `/mnt/ext_relay` | Docker 数据盘 | `ha-config-path`、`firstboot-status`、Docker 文档 |
| `/mnt/data` | 共享数据盘 | `ha-config-path`、samba/unishare 指引 |
| `/mnt/nvme0`、`/mnt/nvme1` … | NVMe 自动挂载 | [files/etc/init.d/nvme-automount](../files/etc/init.d/nvme-automount) |

`ha-config-path` 的优先级：`/mnt/data` → `/mnt/ext_relay` → 其它 `/mnt/*`（取剩余空间最大者）。
因此**不要**把这两个挂载点改名或挪到别处，否则 Home Assistant 配置目录会找不到。

## 3. uci 键

| 键 | 值 | 说明 |
| --- | --- | --- |
| `network.lan.ipaddr` | `192.168.100.1`（full） | generic 保持 `192.168.1.1` |
| `network.lan.netmask` | `255.255.255.0` | |
| `dockerd.globals.data_root` | `/mnt/ext_relay/docker` 或 `/mnt/nvme0/docker` | **必须以 `/mnt/` 开头**，否则数据在 overlay |
| `dockerd.globals.log_level` / 日志轮转 | 10 MiB × 3 | 由 `files/etc/init.d/dockerd` 增强实现 |

## 4. 服务与脚本名

| 名字 | 作用 |
| --- | --- |
| `/etc/init.d/dockerd` | Docker 守护进程（含日志轮转增强） |
| `/etc/init.d/nvme-automount` | NVMe 检测/挂载/初始化 |
| `/etc/init.d/ha-config-path` | 解析 Home Assistant 配置目录 |
| `/etc/init.d/luci-services-order` | LuCI 菜单顺序 |
| `/etc/init.d/g68-branding` | 机型标识 |
| `/usr/bin/firstboot-status` | 首启自检 |
| `/usr/bin/kspeeder-cache-gc` | KSpeeder 缓存清理 |
| `/etc/g68/quickstart-index.js` | quickstart 首页定制 |

uci-defaults 一次性脚本（执行后自动删除，**不要再手工创建同名文件**）：
`95-luci-services-order`、`96-docker-firewall`、`97-dockerd-mirrors`、`98-docker-extras`、
`98-enable-custom-initd`、`98-fix-ttyd`、`99-opkg-istore`、`99-set-lan-ip`。

## 5. 冻结基线（baseline）

`docs/baseline.sha256` 锁定了 29 个关键文件（defconfig、工作流、内置脚本、软件源配置）。
CI 在「校验配置并打印目标」步骤做 `sha256sum -c`，**任一文件被动过就直接失败**。

有意修改后必须：

```sh
./scripts/update-baseline.sh          # 重新生成 docs/baseline.sha256
git add docs/baseline.sha256 && git commit -m "chore: 更新基线指纹"
```

不要手工编辑 `docs/baseline.sha256`，也不要用 `--quiet` 绕过校验。

## 6. 换盘 / 重刷后的恢复顺序

1. 刷机 → 首启（LAN 地址、密码按 [first-boot-checklist.md](first-boot-checklist.md) 设置）；
2. 挂载旧数据盘，确认标签仍是 `ext_relay` / `Data`（`blkid` 查看）；
3. 恢复 `/etc/config/` 备份：`系统 → 备份/升级 → 上传备份`；
4. 核对 `dockerd.globals.data_root` 指向新盘路径，重启 `dockerd`；
5. iStore 若报路径失效，重新指定安装位置（程序本体可重装，数据在数据盘上）；
6. `firstboot-status` 全绿后再恢复业务容器。

## 7. 不要做的事

- 不要改 `/mnt/ext_relay`、`/mnt/data` 的名字或大小写；
- 不要用官方 kmods 源装内核模块（与自编内核绑定，必须重编）；
- 不要期望固件自动分区/格式化（已刻意移除，避免断电风险）；
- 不要直接覆盖 `/etc/config/network` 整份文件（端口映射由板级 `02_network` 生成）。
