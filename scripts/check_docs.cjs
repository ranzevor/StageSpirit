const fs = require("node:fs");
const path = require("node:path");
const commonmark = require("../.github/scripts/vendor/commonmark-0.29.2.min.cjs");

const ignoredDirectories = new Set([
    ".git", ".venv", "node_modules", "dist", "build", "__pycache__",
    ".pytest_cache", ".ruff_cache", ".mypy_cache",
]);

function markdownFiles(directory) {
    const files = [];
    for (const entry of fs.readdirSync(directory, { withFileTypes: true })) {
        const target = path.join(directory, entry.name);
        if (entry.isDirectory() && !ignoredDirectories.has(entry.name)) {
            files.push(...markdownFiles(target));
        } else if (entry.isFile() && entry.name.endsWith(".md")) {
            files.push(target);
        }
    }
    return files.sort();
}

function nodeText(node) {
    let text = "";
    const walker = node.walker();
    let event;
    while ((event = walker.next())) {
        if (event.entering && ["text", "code"].includes(event.node.type)) {
            text += event.node.literal;
        }
    }
    return text;
}

function headingSlug(text) {
    return text.trim().toLowerCase()
        .replace(/[^\p{L}\p{M}\p{N}\s_-]/gu, "")
        .replace(/\s/g, "-");
}

function parseDocument(file) {
    const source = new TextDecoder("utf-8", { fatal: true }).decode(fs.readFileSync(file));
    const tree = new commonmark.Parser().parse(source);
    const anchors = new Set();
    const headings = new Map();
    const links = [];
    const errors = [];
    const walker = tree.walker();
    let event;
    while ((event = walker.next())) {
        if (!event.entering) continue;
        const node = event.node;
        if (node.type === "heading") {
            const base = headingSlug(nodeText(node));
            const count = headings.get(base) || 0;
            headings.set(base, count + 1);
            anchors.add(count ? `${base}-${count}` : base);
        }
        if (["link", "image"].includes(node.type)) {
            links.push({ destination: node.destination, image: node.type === "image" });
            if (!nodeText(node).trim()) errors.push("链接或图片缺少可理解的文字");
        }
        if (["html_inline", "html_block"].includes(node.type)) {
            for (const match of node.literal.matchAll(/\b(?:id|name)=["']([^"']+)["']/g)) {
                anchors.add(match[1]);
            }
            for (const match of node.literal.matchAll(/<(a|img)\b[^>]*>/gi)) {
                const attribute = match[1].toLowerCase() === "img" ? "src" : "href";
                const destination = match[0].match(new RegExp(`\\b${attribute}=["']([^"']+)["']`, "i"));
                if (destination) links.push({ destination: destination[1], image: attribute === "src" });
                if (attribute === "src" && !/\balt=["'][^"']+["']/i.test(match[0])) {
                    errors.push("HTML 图片缺少替代文字");
                }
            }
        }
        if (node.type === "code_block" && node.info.trim() === "json") {
            try {
                JSON.parse(node.literal);
            } catch {
                errors.push("JSON 示例无法解析");
            }
        }
    }
    return { links, anchors, errors };
}

function isInside(root, target) {
    const relative = path.relative(root, target);
    return relative !== ".." && !relative.startsWith(`..${path.sep}`) && !path.isAbsolute(relative);
}

function checkDocuments(directory) {
    const root = fs.realpathSync(directory);
    const documents = new Map();
    const errors = [];
    for (const file of markdownFiles(root)) {
        try {
            documents.set(file, parseDocument(file));
        } catch (error) {
            errors.push(`${path.relative(root, file)}: ${error.message}`);
        }
    }
    for (const [file, document] of documents) {
        const label = path.relative(root, file);
        errors.push(...document.errors.map((error) => `${label}: ${error}`));
        for (const link of document.links) {
            try {
                const destination = link.destination;
                if (/^(https?:|mailto:)/i.test(destination)) {
                    const url = new URL(destination);
                    if (url.hostname === "img.shields.io" && !/^\/(badge|github)\//.test(url.pathname)) {
                        throw new Error(`徽章地址不符合官方端点格式 ${destination}`);
                    }
                    continue;
                }
                if (/^[a-z][a-z0-9+.-]*:/i.test(destination)) throw new Error(`不支持的链接协议 ${destination}`);
                const [pathname, fragment] = destination.split("#", 2);
                const decoded = decodeURIComponent(pathname);
                if (path.isAbsolute(decoded)) throw new Error(`本地链接使用了绝对路径 ${destination}`);
                let target = path.resolve(path.dirname(file), decoded || path.basename(file));
                if (!isInside(root, target)) throw new Error(`链接超出仓库 ${destination}`);
                if (!fs.existsSync(target)) throw new Error(`目标不存在 ${destination}`);
                if (fs.statSync(target).isDirectory()) target = path.join(target, "README.md");
                if (!fs.existsSync(target)) throw new Error(`目录缺少 README.md ${destination}`);
                if (!isInside(root, fs.realpathSync(target))) throw new Error(`链接解析后超出仓库 ${destination}`);
                if (fragment && documents.has(target) && !documents.get(target).anchors.has(decodeURIComponent(fragment))) {
                    throw new Error(`章节不存在 ${destination}`);
                }
                if (link.image && path.extname(target).toLowerCase() === ".svg") {
                    const svg = fs.readFileSync(target, "utf8");
                    if (!/<title\b[^>]*>[^<]+<\/title>/.test(svg) || !/<desc\b[^>]*>[^<]+<\/desc>/.test(svg)) {
                        throw new Error(`SVG 图片缺少 title 或 desc ${destination}`);
                    }
                }
            } catch (error) {
                errors.push(`${label}: ${error.message}`);
            }
        }
    }
    const readme = documents.get(path.join(root, "README.md"));
    if (!readme?.links.some((link) => link.image && !/^[a-z]+:/i.test(link.destination))) {
        errors.push("README.md: 缺少本地封面或品牌图标");
    }
    if (!readme?.links.some((link) => link.image && link.destination.startsWith("https://img.shields.io/"))) {
        errors.push("README.md: 缺少 Shields.io 状态徽章");
    }
    return { files: documents.size, errors };
}

if (require.main === module) {
    const result = checkDocuments(path.resolve(__dirname, ".."));
    for (const error of result.errors) console.error(error);
    if (result.errors.length) {
        process.exitCode = 1;
    } else {
        console.log(`文档检查通过，共 ${result.files} 篇 Markdown。`);
    }
}

module.exports = { checkDocuments };
