const assert = require("node:assert/strict");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const { test } = require("node:test");
const { checkDocuments, parseDocument, shieldsUrl, validateReadmeBadges, projectReadmeErrors } = require("../../scripts/check_docs.cjs");

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


const badgeRequirements = [
    { label: "Version", message: "1.2.3", target: "version.md" },
    { label: "License", message: "Apache-2.0", target: "LICENSE" },
    { label: "CI", message: "main", workflow: "test/project/ci.yml", target: "https://github.com/test/project/actions/workflows/ci.yml" },
];

function badgeLinks() {
    return [
        { image: true, destination: "https://img.shields.io/badge/Version-1.2.3-blue", label: "Version 1.2.3", target: "version.md" },
        { image: true, destination: "https://img.shields.io/badge/License-Apache--2.0-green", label: "License Apache-2.0", target: "LICENSE" },
        { image: true, destination: "https://img.shields.io/github/actions/workflow/status/test/project/ci.yml?branch=main&label=CI", label: "CI main", target: "https://github.com/test/project/actions/workflows/ci.yml" },
    ];
}

test("accepts official badges with escaped text and matching destinations", () => {
    assert.equal(shieldsUrl("Title", "A-B_C + D", "blue"), "https://img.shields.io/badge/Title-A--B__C%20%2B%20D-blue");
    assert.deepEqual(validateReadmeBadges(badgeLinks(), badgeRequirements), []);
    const links = badgeLinks();
    links[0].target = "./version.md";
    assert.deepEqual(validateReadmeBadges(links, badgeRequirements), []);
});

for (const [name, change, expected] of [
    ["missing category", (links) => links.splice(0, 1), "须存在且唯一"],
    ["duplicate category", (links) => links.push({ ...links[0] }), "须存在且唯一"],
    ["stale version", (links) => { links[0].destination = "https://img.shields.io/badge/Version-1.2.2-blue"; }, "值与项目来源不一致"],
    ["incorrect alt", (links) => { links[0].label = "Version 9.9.9"; }, "替代文字"],
    ["wrong target", (links) => { links[0].target = "LICENSE"; }, "对应说明"],
    ["unofficial host", (links) => { links[0].destination = "https://example.test/badge/Version-1.2.3-blue"; }, "官方 HTTPS"],
    ["query override", (links) => { links[0].destination += "?message=9.9.9"; }, "值与项目来源不一致"],
    ["wrong workflow", (links) => { links[2].destination = links[2].destination.replace("ci.yml", "fake.yml"); }, "仓库、工作流或分支"],
    ["wrong branch", (links) => { links[2].destination = links[2].destination.replace("branch=main", "branch=other"); }, "仓库、工作流或分支"],
]) {
    test(`rejects badge ${name}`, () => {
        const links = badgeLinks();
        change(links);
        assert.ok(validateReadmeBadges(links, badgeRequirements).some((error) => error.includes(expected)));
    });
}

test("extracts the same badge association from reference Markdown and HTML", (t) => {
    const root = fixture(t);
    const markdown = '[![Version 1.2.3][image]][target]\n\n[image]: https://img.shields.io/badge/Version-1.2.3-blue\n[target]: version.md\n';
    const file = path.join(root, "badges.md");
    fs.writeFileSync(file, markdown);
    assert.deepEqual(validateReadmeBadges(parseDocument(file).links, [badgeRequirements[0]]), []);
    fs.writeFileSync(file, '<a href="version.md"><img src="https://img.shields.io/badge/Version-1.2.3-blue" alt="Version 1.2.3"></a>');
    assert.deepEqual(validateReadmeBadges(parseDocument(file).links, [badgeRequirements[0]]), []);
});

test("binds badge and document versions to the program source", (t) => {
    const root = fixture(t);
    const sourceRoot = path.resolve(__dirname, "../..");
    const files = ["README.md", "src/stagespirit_mcp/__init__.py", ".python-version", "pyproject.toml", "docs/reference/mcp.md", "docs/standards/README.md", "docs/development/compatibility.md", "docs/guides/quickstart.md", ".github/workflows/ci.yml"];
    for (const file of files) {
        fs.mkdirSync(path.dirname(path.join(root, file)), { recursive: true });
        fs.copyFileSync(path.join(sourceRoot, file), path.join(root, file));
    }
    assert.deepEqual(projectReadmeErrors(root), []);
    fs.appendFileSync(path.join(root, "src/stagespirit_mcp/__init__.py"), "\n");
    assert.deepEqual(projectReadmeErrors(root), []);
    const original = fs.readFileSync(path.join(root, "src/stagespirit_mcp/__init__.py"), "utf8");
    fs.writeFileSync(path.join(root, "src/stagespirit_mcp/__init__.py"), original.replace(/__version__ = "[^"]+"/, '__version__ = "9.8.7"'));
    const errors = projectReadmeErrors(root).join("\n");
    assert.ok(errors.includes("Version 徽章的值与项目来源不一致"));
    assert.ok(errors.includes("README.md: 文档版本与程序版本不同"));
    assert.ok(errors.includes("compatibility.md: 文档版本与程序版本不同"));
    assert.ok(errors.includes("quickstart.md: 文档版本与程序版本不同"));
    fs.writeFileSync(path.join(root, "src/stagespirit_mcp/__init__.py"), original);
    const manifestPath = path.join(root, "pyproject.toml");
    const manifest = fs.readFileSync(manifestPath, "utf8");
    fs.writeFileSync(manifestPath, manifest.replace("Development Status :: 2 - Pre-Alpha", "Development Status :: 5 - Production/Stable"));
    assert.ok(projectReadmeErrors(root).some((error) => error.includes("Status 徽章的值与项目来源不一致")));
});
