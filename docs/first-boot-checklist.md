# 刷机后首次启动检查表

> 适用于 `nsy_g68-plus`（RK3568）固件。**按顺序执行**，每步都有验收命令；
> 全部完成后建议生成一次配置备份。
>
> **变体差异先看这里**：
>
> | 项目 | full（默认） | generic |
> | --- | --- | --- |
> | LAN 地址 | `192.168.100.1/24`（由 `99-set-lan-ip` 设置） | **保持 OpenWrt 默认 `192.168.1.1/24`** |
> | root 密码 | 空（必须立刻设置） | 空（必须立刻设置） |
> | 首启自检工具 | `firstboot-status` 可用 | 无该命令 |
> | NVMe 自动挂载 | 有（`nvme-automount`） | **无**，需手动挂载 |
> | Docker 数据目录 | 默认 `/opt/docker`（overlay），需手动改 | 同左（且无内置 docker 初始化脚本） |
> | 其余应用 | 相同（包集合一致） | 相同 |

---

## 1. 登录并改密码（必做第一步）

```sh
# full: 浏览器访问 http://192.168.100.1 ；generic: http://192.168.1.1
passwd root
```

LuCI：`系统 → 管理权 → 修改密码`。默认无密码，暴露在公网前务必修改。

## 2. 校时 + 确认联网

```sh
uci set system.@system[0].timezone='CST-8'
uci set system.@system[0].zonename='Asia/Shanghai'
uci commit system
ping -c3 223.5.5.5
opkg update
```

WAN 接上级路由 LAN 时默认 DHCP 即可上网。

## 3. 磁盘：手动操作，固件不会自动分区/格式化

固件**不做任何自动分区、格式化、重启**；只做两件被动的事：

- full 变体：`nvme-automount` 检测到 NVMe 上**已有**受支持文件系统（ext4/xfs/btrfs/f2fs/exfat/ntfs3）时挂到 `/mnt/nvmeX`；
- full 变体：空白 NVMe 会被初始化成单分区 ext4（标签 `NVME$idx`）——**介意请先断电拔盘**。

eMMC 想扩出数据分区（eMMC 用户区在 `rootfs_data` 之后，需手动划）：

```sh
parted -s /dev/mmcblk0 unit MiB mkpart extended 4598 100%
parted -s /dev/mmcblk0 unit MiB mkpart logical ext4 4599 55798
parted -s /dev/mmcblk0 unit MiB mkpart logical ext4 55799 100%
reboot                                  # 必须重启，内核才认新分区

mkfs.ext4 -F -m 0 -L ext_relay /dev/mmcblk0p5
mkfs.ext4 -F -m 0 -L Data      /dev/mmcblk0p6
mkdir -p /mnt/ext_relay /mnt/data
```

> 分区起始扇区按实际容量调整，别照抄。改分区前务必确认目标盘。

## 4. 挂载（LuCI 或命令行）

LuCI：`系统 → 挂载点 → 添加`，或：

```sh
block detect > /etc/config/fstab
uci commit fstab
/etc/init.d/fstab restart
```

验收：

```sh
mount | grep /mnt
```

## 5. Docker 数据目录（默认在 overlay，必须改）

```sh
uci set dockerd.globals.data_root='/mnt/ext_relay/docker'   # 或 /mnt/nvme0/docker
uci commit dockerd
/etc/init.d/dockerd restart
docker info | grep -i 'docker root dir'
```

验收标准：输出的路径**以 `/mnt/` 开头**；若 `Storage Driver` 是 `vfs`，说明目录仍在 overlay 或未真正挂载，先回去检查第 4 步。

## 6. iStore 安装位置

iStore → 安装弹窗 → 「存储位置」选已挂载的盘（如 `/mnt/nvme0`）。
程序本体固定落在 `/overlay`，装前先看空间：

```sh
df -h /overlay
```

## 7. 收尾自检

full 变体：

```sh
firstboot-status      # 期望全部 ✅，退出码 0
```

generic 变体没有该命令，逐项确认：

```sh
ls /etc/uci-defaults/            # 应为空
docker info | grep -i 'docker root dir'
mount | grep /mnt
opkg update                      # 无 "has no valid architecture"
```

最后：`系统 → 备份/升级 → 生成配置备份`，把备份存到数据盘或电脑。

---

## 常见问题

| 现象 | 处理 |
| --- | --- |
| 刷完访问 `192.168.100.1` 打不开 | 可能是 generic 变体：试 `192.168.1.1` |
| `mkfs` 报 `No such device` | 新建分区后**必须先重启** |
| `opkg` 报 `has no valid architecture` | `sed -i '/^arch/d' /etc/opkg.conf`，再补 `all` / `noarch` / `aarch64_generic` / `aarch64_cortex-a53` 四行 |
| Docker 空间暴涨 / 只有 `vfs` | `data_root` 还在 overlay，按第 5 步改到真实挂载点后重启 dockerd |
| eMMC「秒擦除」 | eMMC 可能异常，先别刷，检查硬件 |

更多细节：[build-guide.md](build-guide.md)、[invariants.md](invariants.md)。
