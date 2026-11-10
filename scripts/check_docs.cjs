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
    const htmlAnchors = [];
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
            links.push({
                destination: node.destination,
                image: node.type === "image",
                label: nodeText(node),
                target: node.parent?.type === "link" ? node.parent.destination : null,
            });
            if (!nodeText(node).trim()) errors.push("链接或图片缺少可理解的文字");
        }
        if (["html_inline", "html_block"].includes(node.type)) {
            for (const match of node.literal.matchAll(/\b(?:id|name)=["']([^"']+)["']/g)) {
                anchors.add(match[1]);
            }
            for (const match of node.literal.matchAll(/<(\/?)(a|img)\b([^>]*)>/gi)) {
                const attributes = {};
                for (const attribute of match[3].matchAll(/([\w-]+)\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s>]+))/g)) {
                    attributes[attribute[1].toLowerCase()] = (attribute[2] ?? attribute[3] ?? attribute[4]).replace(/&amp;/g, "&");
                }
                if (match[2].toLowerCase() === "a") {
                    if (match[1]) htmlAnchors.pop();
                    else {
                        htmlAnchors.push(attributes.href || null);
                        if (attributes.href) links.push({ destination: attributes.href, image: false });
                    }
                } else if (!match[1] && attributes.src) {
                    const decorative = attributes["aria-hidden"] === "true" || attributes.role === "presentation";
                    links.push({
                        destination: attributes.src,
                        image: true,
                        label: attributes.alt || "",
                        target: htmlAnchors.at(-1) || null,
                        decorative,
                    });
                    if (!attributes.alt && !decorative) errors.push("HTML 图片缺少替代文字");
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

function shieldsUrl(label, message, color) {
    const encode = (value) => encodeURIComponent(value.replace(/-/g, "--").replace(/_/g, "__"));
    return `https://img.shields.io/badge/${encode(label)}-${encode(message)}-${color}`;
}

function targetKey(target) {
    if (!target) return null;
    if (/^https?:/i.test(target)) return new URL(target).href;
    const [file, fragment] = decodeURIComponent(target).split("#", 2);
    return path.posix.normalize(file) + (fragment ? `#${fragment}` : "");
}

function validateReadmeBadges(links, requirements) {
    const errors = [];
    const images = links.filter((link) => link.image);
    for (const requirement of requirements) {
        const { label, message, target, workflow } = requirement;
        const candidates = images.filter((image) => {
            try {
                const url = new URL(image.destination);
                return workflow
                    ? url.pathname.startsWith("/github/actions/workflow/status/") && url.searchParams.get("label") === label
                    : decodeURIComponent(url.pathname).startsWith(`/badge/${label}-`);
            } catch {
                return false;
            }
        });
        if (candidates.length !== 1) {
            errors.push(`README.md: ${label} 徽章须存在且唯一`);
            continue;
        }
        const badge = candidates[0];
        const url = new URL(badge.destination);
        if (url.origin !== "https://img.shields.io" || url.username || url.password) {
            errors.push(`README.md: ${label} 徽章须使用 Shields.io 官方 HTTPS 地址`);
        }
        if (workflow) {
            if (url.pathname !== `/github/actions/workflow/status/${workflow}` || url.searchParams.get("branch") !== message) {
                errors.push(`README.md: ${label} 徽章的仓库、工作流或分支不匹配`);
            }
        } else {
            const color = url.pathname.split("-").at(-1);
            if (!/^(?:[a-z]+|[a-f0-9]{6})$/i.test(color) ||
                decodeURIComponent(url.pathname) !== decodeURIComponent(new URL(shieldsUrl(label, message, color)).pathname) ||
                ["label", "message", "color"].some((key) => url.searchParams.has(key))) {
                errors.push(`README.md: ${label} 徽章的值与项目来源不一致或编码无效`);
            }
        }
        if (badge.label !== `${label} ${message}` || badge.decorative) {
            errors.push(`README.md: ${label} 徽章替代文字与显示含义不一致`);
        }
        if (targetKey(badge.target) !== targetKey(target)) {
            errors.push(`README.md: ${label} 徽章未链接到对应说明`);
        }
    }
    return errors;
}

function projectReadmeErrors(root) {
    const read = (file) => fs.readFileSync(path.join(root, file), "utf8");
    const capture = (file, expression) => {
        const match = expression.exec(read(file));
        if (!match) throw new Error(`${file} 缺少可识别的版本或协议声明`);
        return match[1];
    };
    try {
        const version = capture("src/stagespirit_mcp/__init__.py", /^__version__\s*=\s*["']([^"']+)["']/m);
        const python = read(".python-version").trim().split(".").slice(0, 2).join(".");
        const developmentStatus = capture("pyproject.toml", /Development Status :: ([1-7]) -/);
        const maturity = { 1: "planning", 2: "development", 3: "alpha", 4: "beta", 5: "stable", 6: "mature", 7: "inactive" }[developmentStatus];
        const license = capture("pyproject.toml", /^license\s*=\s*["']([^"']+)["']/m);
        const protocol = capture("docs/reference/mcp.md", /互通基线为 MCP `([^`]+)`/);
        const standards = capture("docs/standards/README.md", /采用集合为 \*\*([^*]+)\*\*/);
        const platform = capture("docs/development/compatibility.md", /^\| 操作系统 \| ([^|]+) \|$/m).trim();
        const requirements = [
            { label: "Version", message: version, target: "docs/development/compatibility.md#版本规则" },
            { label: "Status", message: maturity, target: "docs/development/delivery.md#当前交付" },
            {
                label: "CI", message: "main", workflow: "ranzevor/StageSpirit/ci.yml",
                target: "https://github.com/ranzevor/StageSpirit/actions/workflows/ci.yml?query=branch%3Amain",
            },
            { label: "License", message: license, target: "LICENSE" },
            { label: "Python", message: python, target: "docs/development/compatibility.md#当前支持范围" },
            { label: "Platform", message: platform, target: "docs/development/compatibility.md#当前支持范围" },
            { label: "MCP", message: protocol, target: "docs/reference/mcp.md#连接与发现" },
            { label: "Transport", message: "stdio", target: "docs/reference/mcp.md#连接与发现" },
            { label: "Distribution", message: "wheel + sdist", target: "docs/development/releasing.md#构建与安装" },
            { label: "Documents", message: "Markdown", target: "docs/README.md" },
            { label: "Contracts", message: "JSON Schema", target: "contracts/README.md" },
            { label: "Standards", message: standards, target: "docs/standards/README.md" },
        ];
        const document = parseDocument(path.join(root, "README.md"));
        const errors = validateReadmeBadges(document.links, requirements);
        const versionBindings = [
            ["README.md", /当前开发版本为 `([^`]+)`/],
            ["docs/development/compatibility.md", /\| StageSpirit \| `([^`]+)`/],
            ["docs/guides/quickstart.md", /版本命令应输出 `StageSpirit ([^`]+)`/],
        ];
        for (const [file, expression] of versionBindings) {
            if (capture(file, expression) !== version) errors.push(`${file}: 文档版本与程序版本不同`);
        }
        read(".github/workflows/ci.yml");
        return errors;
    } catch (error) {
        return [error.message];
    }
}

if (require.main === module) {
    const result = checkDocuments(path.resolve(__dirname, ".."));
    result.errors.push(...projectReadmeErrors(path.resolve(__dirname, "..")));
    for (const error of result.errors) console.error(error);
    if (result.errors.length) {
        process.exitCode = 1;
    } else {
        console.log(`文档检查通过，共 ${result.files} 篇 Markdown。`);
    }
}

module.exports = { checkDocuments, parseDocument, shieldsUrl, validateReadmeBadges, projectReadmeErrors };
