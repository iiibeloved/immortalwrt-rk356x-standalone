#!/bin/sh
# =============================================================================
#  Release 追加发布的纯逻辑（workflow 调用 + 单元测试覆盖）
#
#  这里只放"无网络、无副作用"的字符串/文件处理：
#   - release_asset_name : generic 追加到已有 Release 时的资产命名
#   - merge_sums         : 与 Release 上已有 sha256sums 合并（保留其它变体条目）
# =============================================================================

# release_asset_name <镜像路径> [variant]
#   generic + 追加模式：镜像名加 -generic 后缀（已带后缀则不重复追加）
#   其它情况：原样返回 basename
release_asset_name() {
	_img="$1"
	_variant="${2:-full}"
	_base=$(basename "$_img")
	if [ "$_variant" = "generic" ]; then
		case "$_base" in
			*-generic.img.gz) printf '%s\n' "$_base" ;;
			*.img.gz) printf '%s\n' "${_base%.img.gz}-generic.img.gz" ;;
			*) printf '%s\n' "${_base}-generic" ;;
		esac
	else
		printf '%s\n' "$_base"
	fi
}

# merge_sums <已有 sums 文件> <资产名> <sha256>
#   输出：已有条目（剔除同名旧条目）+ 本次条目
#   注意：只剔除"同名"条目。full 变体的资产名不带 -generic，
#         不能被 generic 追加时的清理逻辑误删。
merge_sums() {
	_base_file="$1"
	_asset="$2"
	_sha="$3"
	_esc=$(printf '%s' "$_asset" | sed 's/[.[\*^$]/\\&/g')
	if [ -n "$_base_file" ] && [ -f "$_base_file" ]; then
		grep -vE "  ${_esc}$" "$_base_file" || true
	fi
	printf '%s  %s\n' "$_sha" "$_asset"
}
