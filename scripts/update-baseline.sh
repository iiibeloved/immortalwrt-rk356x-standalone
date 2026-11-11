#!/bin/sh
# 重新生成 docs/baseline.sha256（有意修改基线文件后执行）
#
# 用法: ./scripts/update-baseline.sh
# 触发场景: 改了 defconfig / 工作流 / files/** 任一文件后, 必须重跑本脚本并提交,
#           否则 CI 的「校验配置并打印目标」步骤会因指纹不一致直接失败。
set -eu
cd "$(dirname "$0")/.."

OUT=docs/baseline.sha256
TMP=$(mktemp)
trap 'rm -f "$TMP"' EXIT

{
	echo "# 基线指纹（改动后请执行 scripts/update-baseline.sh 重新生成）"
	echo "# 校验: sha256sum -c docs/baseline.sha256"
	{
		echo defconfig/g68-plus-docker.config
		echo defconfig/g68-plus-istoreos.config
		echo .github/workflows/build-g68-plus-docker.yml
		echo .github/workflows/publish-release.yml
		echo scripts/gen_image_generic.sh
		echo scripts/release-append-lib.sh
		# files/ 全量纳入, 避免新增内置脚本后漏校验
		# 排除 CI 运行时生成、仓库中不存在的文件（如 files/etc/g68-build）
		find files -type f ! -name 'g68-build' | sort
	} | while read -r f; do
		if [ -f "$f" ]; then
			sha256sum "$f"
		else
			echo "警告: 文件不存在, 已跳过: $f" >&2
		fi
	done
} > "$TMP"

mv "$TMP" "$OUT"
echo "已生成 $OUT（$(grep -vc '^#' "$OUT") 个文件）"
