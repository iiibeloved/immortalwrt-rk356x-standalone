# full 版内置项清单（G68-PLUS · ImmortalWrt 24.10）

> 本文件列出 **full 变体** 固件内置的全部脚本与配置。
> **generic 变体**（`*-generic.img.gz`）会删除 `files/` 下全部内容，本清单里的项**一个都没有**，
> 分区、挂载、docker 数据目录、LAN 地址、共享目录等全部需要刷机后手动配置。
> 所有内置项都是**开机幂等**执行，可在 `/etc/init.d/<name> disable` 关闭，或直接改对应 uci 后重启。

## 一、init 脚本（开机执行）

| 文件 | START | 作用 | 默认行为 / 关闭方式 |
| --- | --- | --- | --- |
| `files/etc/init.d/dockerd` | 99 | 覆盖 dockerd 包的 init，仅两处增强：读 uci 的 `log_max_size`/`log_max_file` 写 `daemon.json` 的 `log-opts`；`log_driver` 默认 `json-file` | 容器日志 **10MiB × 3** 自动轮转；数据目录/镜像/日志全部以 uci 为准（LuCI→Docker→配置）。关闭：`/etc/init.d/dockerd disable` 会失去 docker 服务，不建议；只想关轮转：`uci set dockerd.@dockerd[0].log_max_size=0` |
| `files/etc/init.d/g68-branding` | 96 | 品牌信息统一（幂等）：`/tmp/sysinfo/model=NSY-G68`；`os-release`/`openwrt_release` 统一为 `ImmortalWrt 24.10`（去掉 `by:xxx`）；读 `/etc/g68-build` 把构建版本号写进 banner 与 `DISTRIB_REVISION`/`DISTRIB_BUILD`；quickstart 首页去掉「（内核：x.y.z）」后缀 | 关闭：`/etc/init.d/g68-branding disable`（型号/版本会恢复成上游默认） |
| `files/etc/init.d/ha-config-path` | 97 | 为 `luci-app-homeassistant` 自动选择 `config_path`（`<挂载点>/Configs/HomeAssistant`），避免 HACS 装到错误位置 | 关闭：`/etc/init.d/ha-config-path disable`，改在 LuCI HA 页面手选 |
| `files/etc/init.d/luci-default-page` | 97 | 把 LuCI 登录后的首页固定为 **QuickStart**：把 `luci-app-routerdog.json` 的 `"order": -1` 改成 70，Lua entry 的 `1)` 改成 `10)`，并清 `/tmp/luci-indexcache*` | 关闭：`/etc/init.d/luci-default-page disable`（登录后会跳到路由狗） |
| `files/etc/init.d/luci-services-order` | 96 | 开机把「服务」菜单按**英文 A-Z → 中文拼音**重排（应用升级会重置 order，所以每次开机兜底一次）；命令与页面由 `luci-app-menusort` 包提供 | 关闭：`/etc/init.d/luci-services-order disable`；手动重排：`menusort`；页面：系统 → 菜单排序 |
| `files/etc/init.d/nvme-automount` | 97 | 自动检测 NVMe 并挂载：有分区且文件系统受支持 → 按 UUID 写 fstab 挂到 `/mnt/nvmeX`；**全盘空白默认不格式化**（只记日志，保护数据）；需自动建分区时 `touch /etc/nvme-automount.format` 再重启 | 关闭：`/etc/init.d/nvme-automount disable` |

## 二、首次启动一次性配置（uci-defaults，执行后自动删除）

| 文件 | 作用 |
| --- | --- |
| `95-luci-services-order` | 启用并立即执行 `luci-services-order`（首次开机就有正确菜单顺序） |
| `96-docker-firewall` | 创建 `docker` 防火墙区域 + `lan → docker` 转发，**容器端口对局域网可达** |
| `97-dockerd-mirrors` | 写入国内 docker 镜像加速默认源（`docker.1panel.live`、`docker.m.daocloud.io`、`docker.1ms.run`、`docker.xuanyuan.me`；装了 KSpeeder 时把 `registry.linkease.net:5443` 放最前） |
| `98-docker-extras` | 写入 KSpeeder 缓存回收的 uci 默认值 + 定时任务 `*/15 * * * *` |
| `98-enable-custom-initd` | 启用并执行 `g68-branding` / `luci-default-page` / `luci-services-order` / `nvme-automount` / `ha-config-path` |
| `98-fix-ttyd` | 修复 ttyd 默认配置（调试终端可正常打开） |
| `99-opkg-istore` | 写入内置 opkg 源：官方 6 个 + iStoreOS 3 个（store / nas_luci / nas） |
| `99-set-lan-ip` | 首次启动设置 LAN 为 `192.168.100.1`（你可随时在页面改） |

## 三、命令行工具

| 文件 | 作用 |
| --- | --- |
| `files/usr/bin/firstboot-status` | 首启自检：按 1/7…7/7 输出挂载、存储、docker、网络等检查结果（方便判断刷机后状态） |
| `files/usr/bin/kspeeder-cache-gc` | KSpeeder 缓存回收：读 `istoreenhance.@istoreenhance[0].gc_enabled/gc_limit_mb/gc_time`，按阈值清理缓存，日志 `/etc/kspeeder-cache-gc.log` |

## 四、LuCI 页面（KSpeeder 缓存回收）

| 文件 | 作用 |
| --- | --- |
| `files/usr/share/luci/menu.d/luci-app-ksgc.json` | 菜单入口：**服务 → KSpeeder 缓存回收**（order 62） |
| `files/usr/share/rpcd/acl.d/luci-app-ksgc.json` | 页面 ACL |
| `files/www/luci-static/resources/view/ksgc/ksgc.js` | 页面：开关 / 阈值 / 执行时间（HH:MM） |

## 五、其他

| 文件 | 作用 |
| --- | --- |
| `files/etc/g68/quickstart-index.js` | quickstart 首页资源备份（去内核后缀版）；`g68-branding` 在包升级覆盖后用它与 `/www/.../index.js` 对比并恢复 |
| `files/etc/config/ttyd` | ttyd 默认配置（`98-fix-ttyd` 会修正） |

## 六、与 generic 版的差异一览

| 项 | full | generic |
| --- | --- | --- |
| 软件包数量 | 566（含 `luci-app-menusort`） | **同样 566** |
| 本文件列出的所有脚本/配置 | ✅ 全部内置 | ❌ 全部剔除（`files/` 整目录删除） |
| 品牌信息 / 构建号 | ✅ | ❌（显示上游默认） |
| 菜单开机排序 | ✅（init 兜底） | ❌（页面仍可手动点排序） |
| docker 日志轮转 / live-restore | ✅ | ❌（自己改 `/etc/config/dockerd`） |
| lan→docker 转发 | ✅ | ❌（手动加防火墙规则） |
| docker 镜像加速默认源 | ✅ | ❌（手动填） |
| KSpeeder 缓存回收页 + 定时任务 | ✅ | ❌ |
| NVMe 自动挂载 | ✅ | ❌（手动 `block detect` + fstab） |
| LAN 192.168.100.1 | ✅ | ❌（默认 192.168.1.1，自己改） |
| 分区（kernel 16 / rootfs 200 / rootfs_data 4096 MiB） | 镜像内固定 | 镜像内固定（分区不属于脚本） |
| docker 数据目录 | **不固定**，页面配置（默认 `/opt/docker`） | 页面配置 |
| 容器应用 | **不预装**，接通过 Docker Manager / iStore 安装 | 同 |
