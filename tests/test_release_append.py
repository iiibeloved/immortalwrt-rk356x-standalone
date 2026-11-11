#!/usr/bin/env python3
"""release 追加发布逻辑的单元测试（仅用标准库，无网络）。

覆盖两部分：
  1. VARIANT —— workflow env 定义、裁剪步骤的真实行为（generic 删哪些、full 保留哪些）
  2. 上传/发布 —— 资产命名（-generic 后缀、防重复）与 sha256sums 合并（保留 full 条目）

运行：
  python3 -m unittest discover -s tests -v
"""

import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORKFLOW = os.path.join(REPO, ".github", "workflows", "build-g68-plus-docker.yml")
PUBLISH_WF = os.path.join(REPO, ".github", "workflows", "publish-release.yml")
LIB = os.path.join(REPO, "scripts", "release-append-lib.sh")


def read_workflow():
    with open(WORKFLOW, encoding="utf-8") as f:
        return f.read()


def extract_run_block(step_name):
    """从 workflow 中取出指定 step 的 run: | 脚本体（去掉 YAML 缩进）。"""
    lines = read_workflow().split("\n")
    start = None
    for i, line in enumerate(lines):
        if line.startswith("      - name: ") and step_name in line:
            start = i
            break
    if start is None:
        raise AssertionError("workflow 中找不到步骤: %s" % step_name)
    end = len(lines)
    for j in range(start + 1, len(lines)):
        if lines[j].startswith("      - name: "):
            end = j
            break
    block = lines[start:end]
    ri = next(k for k, l in enumerate(block) if l.strip() == "run: |")
    body = [l for l in block[ri + 1:] if l.strip()]
    if not body:
        raise AssertionError("步骤 %s 没有 run 脚本" % step_name)
    indent = len(body[0]) - len(body[0].lstrip())
    return "\n".join(l[indent:] if l.strip() else "" for l in body)


def shell(script, env_extra=None, cwd=None):
    """在 sh 中执行脚本，注入 lib 函数路径。"""
    env = dict(os.environ)
    env.update(env_extra or {})
    return subprocess.run(
        ["sh", "-c", '. "$LIB"; %s' % script],
        cwd=cwd, env=dict(env, LIB=LIB),
        capture_output=True, text=True,
    )


class TestVariantWiring(unittest.TestCase):
    """VARIANT 必须在 env 里定义，否则 ${VARIANT:-full} 恒为 full。"""

    def setUp(self):
        self.wf = read_workflow()

    def test_env_defines_variant_with_full_default(self):
        m = re.search(r"^  VARIANT: (.+)$", self.wf, re.M)
        self.assertIsNotNone(m, "workflow env 缺少 VARIANT")
        self.assertIn("github.event.inputs.variant", m.group(1))
        self.assertIn("'full'", m.group(1))

    def test_variant_is_used_not_hardcoded(self):
        # generic 的三处行为都必须受 VARIANT 控制
        self.assertIn('if [ "${VARIANT:-full}" = "generic" ]', self.wf)       # 裁剪
        self.assertIn('TAG="${TAG}-generic"', self.wf)                        # tag
        self.assertIn('| 变体 | **${VARIANT:-full}** |', self.wf)            # 说明

    def test_no_stray_full_assignment(self):
        # 防止有人把 VARIANT 又改成写死 full
        self.assertNotRegex(self.wf, r"^\s*VARIANT=full\s*$")


class TestVariantTrimBehavior(unittest.TestCase):
    """跑 workflow 里真实的裁剪脚本，验证 generic/full 的差异。"""

    FILES = [
        "files/etc/init.d/g68-boot",
        "files/etc/uci-defaults/99-g68",
        "files/etc/config/system",
        "files/etc/opkg/distfeeds.conf",
        "files/usr/bin/ksgc-tool",
        "files/usr/libexec/g68-helper",
        "files/usr/share/luci/menu.d/luci-app-ksgc.json",
    ]

    def run_trim(self, variant):
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp, True)
        for rel in self.FILES:
            dst = os.path.join(tmp, rel)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            open(dst, "w").close()
        script = extract_run_block("按 variant 裁剪内置脚本/配置")
        r = subprocess.run(["bash", "-c", script], cwd=tmp,
                           env=dict(os.environ, VARIANT=variant),
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        return tmp

    def exists(self, tmp, rel):
        return os.path.exists(os.path.join(tmp, rel))

    def test_generic_removes_scripts_keeps_opkg(self):
        tmp = self.run_trim("generic")
        for rel in ("files/etc/init.d/g68-boot",
                    "files/etc/uci-defaults/99-g68",
                    "files/etc/config/system",
                    "files/usr/bin/ksgc-tool",
                    "files/usr/libexec/g68-helper"):
            self.assertFalse(self.exists(tmp, rel), "generic 应删除 %s" % rel)
        self.assertTrue(self.exists(tmp, "files/etc/opkg/distfeeds.conf"),
                        "generic 必须保留软件源配置")
        self.assertTrue(self.exists(tmp, "files/usr/share/luci/menu.d/luci-app-ksgc.json"))

    def test_full_keeps_everything(self):
        tmp = self.run_trim("full")
        for rel in self.FILES:
            self.assertTrue(self.exists(tmp, rel), "full 不应删除 %s" % rel)

    def test_empty_variant_falls_back_to_full(self):
        tmp = self.run_trim("")
        for rel in self.FILES:
            self.assertTrue(self.exists(tmp, rel), "空 VARIANT 应按 full 处理")


class TestAssetName(unittest.TestCase):
    """generic 追加到已有 Release 时的资产命名。"""

    def name(self, img, variant):
        r = shell("release_asset_name '%s' '%s'" % (img, variant))
        self.assertEqual(r.returncode, 0, r.stderr)
        return r.stdout.strip()

    def test_full_keeps_name(self):
        self.assertEqual(self.name("bin/x/img-abc.img.gz", "full"),
                         "img-abc.img.gz")

    def test_generic_appends_suffix(self):
        self.assertEqual(self.name("bin/x/img-abc.img.gz", "generic"),
                         "img-abc-generic.img.gz")

    def test_generic_is_idempotent(self):
        self.assertEqual(self.name("bin/x/img-abc-generic.img.gz", "generic"),
                         "img-abc-generic.img.gz")

    def test_other_suffix_gets_generic(self):
        self.assertEqual(self.name("bin/x/img-abc.bin", "generic"),
                         "img-abc.bin-generic")


class TestMergeSums(unittest.TestCase):
    """sha256sums 合并：只替换同名条目，绝不吞掉 full 的条目。"""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.base = os.path.join(self.tmp, "sums.base")

    def write_base(self, text):
        with open(self.base, "w", encoding="utf-8") as f:
            f.write(text)

    def merge(self, base, asset, sha):
        r = shell("merge_sums '%s' '%s' '%s'" % (base, asset, sha))
        self.assertEqual(r.returncode, 0, r.stderr)
        return r.stdout

    def test_keeps_full_entry_when_adding_generic(self):
        self.write_base(
            "aaaa  img-full-squashfs-sysupgrade.img.gz\n"
            "bbbb  img-full-squashfs-sdcard.img.gz\n")
        out = self.merge(self.base, "img-full-squashfs-sysupgrade-generic.img.gz", "cccc")
        self.assertIn("aaaa  img-full-squashfs-sysupgrade.img.gz", out)
        self.assertIn("bbbb  img-full-squashfs-sdcard.img.gz", out)
        self.assertIn("cccc  img-full-squashfs-sysupgrade-generic.img.gz", out)

    def test_replaces_same_generic_entry(self):
        self.write_base(
            "old0  img-x-generic.img.gz\n"
            "keep  img-x.img.gz\n")
        out = self.merge(self.base, "img-x-generic.img.gz", "new0")
        self.assertNotIn("old0", out)
        self.assertEqual(out.count("img-x-generic.img.gz"), 1)
        self.assertIn("keep  img-x.img.gz", out)

    def test_empty_base(self):
        self.write_base("")
        out = self.merge(self.base, "img-x.img.gz", "dddd")
        self.assertEqual(out.strip(), "dddd  img-x.img.gz")

    def test_missing_base_file(self):
        out = self.merge(os.path.join(self.tmp, "nope"), "img-x.img.gz", "eeee")
        self.assertEqual(out.strip(), "eeee  img-x.img.gz")

    def test_dots_are_escaped_in_match(self):
        # 资产名里的 . 不能当正则通配符，否则会误删 imgXgenericYimgZgz 之类
        self.write_base("ffff  imgXgenericYimgZgz\n")
        out = self.merge(self.base, "img.generic.img.gz", "gggg")
        self.assertIn("ffff  imgXgenericYimgZgz", out)
        self.assertIn("gggg  img.generic.img.gz", out)


class TestWorkflowUsesLib(unittest.TestCase):
    """workflow 必须复用 lib，避免逻辑被内联复制后测试失效。"""

    def test_sources_lib_and_calls_functions(self):
        wf = read_workflow()
        self.assertIn(". scripts/release-append-lib.sh", wf)
        self.assertIn("release_asset_name", wf)
        self.assertIn("merge_sums", wf)

    def test_lib_file_exists_and_parses(self):
        self.assertTrue(os.path.isfile(LIB))
        r = subprocess.run(["sh", "-n", LIB], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)


class TestWorkflowGuards(unittest.TestCase):
    """静态复审发现的细节问题，防止回退。"""

    def setUp(self):
        self.wf = read_workflow()
        with open(PUBLISH_WF, encoding="utf-8") as f:
            self.pub = f.read()

    def test_full_triggers_generic_dispatch(self):
        self.assertIn("event_type=g68-build", self.wf)
        self.assertIn("client_payload[variant]=generic", self.wf)
        self.assertIn("client_payload[publish_tag]", self.wf)
        self.assertIn("id: release", self.wf)
        self.assertIn('echo "tag=$TAG" >> "$GITHUB_OUTPUT"', self.wf)

    def test_ci_runs_unit_tests(self):
        self.assertIn("python3 -m unittest discover -s tests", self.wf)

    def test_publish_release_uses_rest_not_gh_upload(self):
        self.assertNotIn("gh release upload", self.pub)
        self.assertIn("uploads.github.com", self.pub)
        self.assertIn(". scripts/release-append-lib.sh", self.pub)
        self.assertIn("merge_sums", self.pub)
        self.assertIn("201|200) ;;", self.pub)

    def test_sums_download_checks_http(self):
        self.assertIn("-o /tmp/sums.base) || CODE=000", self.wf)
        self.assertIn("-o /tmp/sums.base) || CODE=000", self.pub)

    def test_off_packages_are_stripped(self):
        # 两处都要剥掉 "# CONFIG_PACKAGE_" 与 " is not set"，否则永远匹配不上
        stripped = self.wf.count("s/^# CONFIG_PACKAGE_//")
        self.assertGreaterEqual(stripped, 2)

    def test_artifact_name_uses_env_variant(self):
        self.assertIn("(env.VARIANT == 'generic')", self.wf)
        self.assertNotIn("github.event.inputs.variant == 'generic'", self.wf)


if __name__ == "__main__":
    unittest.main(verbosity=2)
