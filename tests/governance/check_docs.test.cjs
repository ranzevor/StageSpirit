const assert = require("node:assert/strict");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const { test } = require("node:test");
const { checkDocuments } = require("../../scripts/check_docs.cjs");

function fixture(t, extra = "") {
    const root = fs.mkdtempSync(path.join(os.tmpdir(), "stagespirit-docs-"));
    t.after(() => fs.rmSync(root, { recursive: true, force: true }));
    fs.writeFileSync(path.join(root, "logo.svg"), "<svg><title>灵幕</title><desc>舞台</desc></svg>");
    fs.writeFileSync(path.join(root, "README.md"), [
        "# 灵幕", "", "![灵幕](logo.svg)", "",
        "[![开发中](https://img.shields.io/badge/status-development-blue)](#灵幕)", "", extra,
    ].join("\n"));
    return root;
}

test("accepts inline, reference, HTML and duplicate-heading anchors", (t) => {
    const root = fixture(t, [
        "## 重复", "## 重复", "[第二节](#重复-1)", "[目标][target]", "",
        "[target]: child/README.md#含-code-的标题", '<a id="explicit"></a>', "[显式](#explicit)",
        '<img src="logo.svg" alt="灵幕图标">', "```json", '{"name":"灵幕","value":0}', "```",
        "```text", "[代码中的链接](missing.md)", "```",
    ].join("\n"));
    fs.mkdirSync(path.join(root, "child"));
    fs.writeFileSync(path.join(root, "child/README.md"), "# 含 `code` 的标题\n");
    assert.deepEqual(checkDocuments(root).errors, []);
});

test("rejects missing targets, sections, labels and malformed JSON", (t) => {
    const root = fixture(t, '[失效](missing.md)\n[坏锚点](#missing)\n[](logo.svg)\n```json\n{\n```');
    const errors = checkDocuments(root).errors.join("\n");
    for (const expected of ["目标不存在", "章节不存在", "缺少可理解的文字", "JSON 示例无法解析"]) {
        assert.ok(errors.includes(expected), expected);
    }
});

test("rejects repository escapes, unsafe schemes and incomplete SVG", (t) => {
    const root = fixture(t, '[越界](../outside.md)\n[协议](javascript:alert)');
    fs.writeFileSync(path.join(root, "logo.svg"), "<svg><title>灵幕</title></svg>");
    const errors = checkDocuments(root).errors.join("\n");
    for (const expected of ["超出仓库", "不支持的链接协议", "缺少 title 或 desc"]) {
        assert.ok(errors.includes(expected), expected);
    }
});

test("requires a directory README and handles encoded Chinese paths", (t) => {
    const root = fixture(t, "[目录](folder/)\n[中文](%E4%B8%AD%E6%96%87.md#标题)");
    fs.mkdirSync(path.join(root, "folder"));
    fs.writeFileSync(path.join(root, "中文.md"), "# 标题\n");
    assert.ok(checkDocuments(root).errors.some((error) => error.includes("目录缺少 README.md")));
    fs.writeFileSync(path.join(root, "folder/README.md"), "# 目录\n");
    assert.deepEqual(checkDocuments(root).errors, []);
});

test("requires branding and rejects malformed badge endpoints", (t) => {
    const root = fixture(t);
    fs.writeFileSync(path.join(root, "README.md"), "# 项目\n![状态](https://img.shields.io/invalid)\n");
    const errors = checkDocuments(root).errors.join("\n");
    assert.ok(errors.includes("官方端点格式"));
    assert.ok(errors.includes("缺少本地封面或品牌图标"));
});

test("rejects invalid UTF-8 and skips generated directories", (t) => {
    const root = fixture(t);
    fs.mkdirSync(path.join(root, ".venv"));
    fs.writeFileSync(path.join(root, ".venv/broken.md"), "[失效](absent.md)");
    fs.writeFileSync(path.join(root, "broken.md"), Buffer.from([0xff]));
    const result = checkDocuments(root);
    assert.equal(result.errors.length, 1);
    assert.ok(result.errors[0].startsWith("broken.md:"));
});
