// SPDX-License-Identifier: Apache-2.0
// Adapted from Ranzevor Standards v0.2.0. See NOTICE.md.
"use strict";
const fs = require("node:fs");
const commonmark = require("./vendor/commonmark-0.29.2.min.cjs");

const INVALID_TEXT_CHAR =
    /[\p{Cc}\p{Cf}\p{Zs}\p{Zl}\p{Zp}\p{Default_Ignorable_Code_Point}]/u;
function hasInvisibleChars(value, multiline = false) {
    const normalized = multiline ? value.replace(/\r\n/gu, "\n") : value;
    return INVALID_TEXT_CHAR.test(
        normalized.replace(multiline ? /[ \t\n]/gu : / /gu, ""),
    );
}
function markdownPlainText(value) {
    return value
        .trim()
        .replace(/^(?:\s*>\s*)+/u, "")
        .replace(/^\s{0,3}#{1,6}\s+/u, "")
        .replace(/^\s*(?:[-*+]\s+(?:\[[ xX]\]\s*)?|\d+[.)]\s+)/u, "")
        .replace(/!\[([^\]]*)\]\([^)]+\)/gu, "$1")
        .replace(/\[([^\]]+)\]\([^)]+\)/gu, "$1")
        .replace(/[*_`~]/gu, "")
        .trim();
}
function isPlaceholderLine(value) {
    return /^(?:TODO|TBD|FIXME|待补充|占位|暂无内容|待填写|在此填写|请填写|placeholder)(?:\s*[:：-].*)?$/iu.test(
        markdownPlainText(value),
    );
}
function parseBodyMarkdown(body) {
    const parser = new commonmark.Parser();
    const parseInlines = parser.inlineParser.parse;
    // CommonMark 0.29.2 在行内解析前保留原始段落；此时识别任务标记可保留块归属和引用定义。
    parser.inlineParser.parse = function (node) {
        if (
            node.type === "paragraph" &&
            node.parent.type === "item" &&
            node.parent.firstChild === node
        ) {
            node._string_content = node._string_content.replace(
                /^ *\[[ \t\r\n\v\fxX]\](?=[ \t\r\n\v\f]|$)[ \t]*/u,
                "",
            );
        }
        return parseInlines.call(this, node);
    };
    return parser.parse(body);
}
function visibleInlineText(node, omitCode = false) {
    const fragments = [];
    const walker = node.walker();
    let event,
        imageDepth = 0,
        htmlCodeDepth = 0;
    while ((event = walker.next())) {
        const child = event.node;
        if (child.type === "image") {
            imageDepth += event.entering ? 1 : -1;
            continue;
        }
        if (!event.entering || imageDepth) continue;
        if (child.type === "text" || child.type === "code") {
            fragments.push(
                omitCode && (child.type === "code" || htmlCodeDepth)
                    ? child.literal.replace(/[^\n]/gu, " ")
                    : child.literal,
            );
        } else if (child.type === "softbreak" || child.type === "linebreak") {
            fragments.push("\n");
        } else if (child.type === "html_inline") {
            const tag = /^<\s*(\/?)\s*(code|pre|kbd|samp)\b[^>]*>$/iu.exec(
                child.literal,
            );
            if (tag) {
                htmlCodeDepth = Math.max(0, htmlCodeDepth + (tag[1] ? -1 : 1));
            } else if (
                /^<(?:br|hr)(?:\s+[^<>]*?)?\s*\/?>$/iu.test(child.literal) ||
                /^<\/?(?:p|div|li|tr|td|th|summary|h[1-6])\s*>$/iu.test(
                    child.literal,
                )
            ) {
                fragments.push("\n");
            }
        }
    }
    return fragments.join("");
}

// Raw HTML is a CommonMark leaf block, not a paragraph. Read only text that
// can appear in its rendered content, excluding attributes, comments and code.
function decodeHtmlText(value) {
    const literal = value
        .replace(/\\/gu, "\\\\")
        .replace(/([!#*+\-.[\](){}`_~>|])/gu, (char, _group, index, input) =>
            char === "#" && input[index - 1] === "&" ? char : "\\" + char,
        )
        .replace(/</gu, "&lt;");
    return visibleInlineText(new commonmark.Parser().parse(literal));
}
function htmlBlockLines(raw) {
    let text = "",
        placeholders = "",
        codeDepth = 0,
        hiddenDepth = 0;
    const add = (chunk) => {
        if (hiddenDepth) return;
        text += chunk;
        placeholders += codeDepth ? chunk.replace(/[^\n]/gu, " ") : chunk;
    };
    for (let i = 0; i < raw.length; ) {
        if (raw.startsWith("<!--", i)) {
            const end = raw.indexOf("-->", i + 4);
            i = end < 0 ? raw.length : end + 3;
            continue;
        }
        if (raw.startsWith("<!", i) || raw.startsWith("<?", i)) {
            const end = raw.indexOf(">", i + 2);
            i = end < 0 ? raw.length : end + 1;
            continue;
        }
        if (raw[i] === "<") {
            let j = i + 1,
                quote = null;
            for (; j < raw.length; j++) {
                const c = raw[j];
                if (quote) {
                    if (c === quote) quote = null;
                } else if (c === '"' || c === "'") quote = c;
                else if (c === ">") break;
            }
            if (j < raw.length) {
                const tag = raw.slice(i, j + 1);
                const match = /^<\s*(\/?)\s*([a-z][a-z0-9:-]*)\b/iu.exec(tag);
                if (match) {
                    const close = Boolean(match[1]),
                        name = match[2].toLowerCase();
                    if (name === "template")
                        hiddenDepth = Math.max(
                            0,
                            hiddenDepth + (close ? -1 : 1),
                        );
                    if (["code", "pre", "kbd", "samp"].includes(name))
                        codeDepth = Math.max(0, codeDepth + (close ? -1 : 1));
                    if (
                        /^(?:br|hr|p|div|li|tr|td|th|summary|details|h[1-6]|table|blockquote|section)$/u.test(
                            name,
                        )
                    )
                        add("\n");
                }
                i = j + 1;
                continue;
            }
        }
        let j = raw.indexOf("<", i + 1);
        if (j < 0) j = raw.length;
        add(decodeHtmlText(raw.slice(i, j)).replace(/\r?\n[ \t]*/gu, " "));
        i = j;
    }
    return {
        lines: text.split("\n"),
        placeholderLines: placeholders.split("\n"),
    };
}

// GFM tables are paragraphs to CommonMark 0.29.2. Recognize their delimiter
// row within real paragraph boundaries; escaped pipes remain cell content.
function splitGfmCells(row) {
    const parts = [];
    let start = 0;
    for (let i = 0; i < row.length; i++) {
        if (row[i] !== "|") continue;
        let escapes = 0;
        for (let j = i - 1; j >= 0 && row[j] === "\\"; j--) escapes++;
        if (escapes % 2) continue;
        parts.push(row.slice(start, i));
        start = i + 1;
    }
    parts.push(row.slice(start));
    if (row.trimStart().startsWith("|")) parts.shift();
    const trimmed = row.trimEnd();
    if (trimmed.endsWith("|")) {
        let escapes = 0;
        for (let j = trimmed.length - 2; j >= 0 && trimmed[j] === "\\"; j--)
            escapes++;
        if (escapes % 2 === 0 && parts.length > 1) parts.pop();
    }
    return parts.map((x) => x.trim());
}
function tableVisibleLines(node, rawLines) {
    if (node.type !== "paragraph") return null;
    const start = node.sourcepos[0][0] - 1,
        end = node.sourcepos[1][0];
    if (end - start < 2) return null;
    const rows = rawLines.slice(start, end).map((value, i) => {
        const unwrapped =
            i === 0
                ? value.slice(node.sourcepos[0][1] - 1)
                : value.replace(/^(?:[ \t]*>[ \t]?)+/u, "").trimStart();
        return unwrapped.trim();
    });
    if (!rows[0].includes("|") || !rows[1].includes("|")) return null;
    const head = splitGfmCells(rows[0]),
        delimiter = splitGfmCells(rows[1]);
    if (
        !head.length ||
        head.length !== delimiter.length ||
        !delimiter.every((x) => /^:?-+:?$/u.test(x))
    )
        return null;
    const lines = [],
        placeholderLines = [];
    for (const [index, row] of rows.entries()) {
        if (index === 1) continue;
        const cells = splitGfmCells(row).slice(0, head.length);
        while (cells.length < head.length) cells.push("");
        for (const cell of cells) {
            const parsed = new commonmark.Parser().parse(cell);
            lines.push(...visibleInlineText(parsed).split("\n"));
            placeholderLines.push(
                ...visibleInlineText(parsed, true).split("\n"),
            );
        }
    }
    return { lines, placeholderLines };
}
function visibleBlockLines(node, rawLines) {
    if (node.type === "html_block") return htmlBlockLines(node.literal);
    const table = tableVisibleLines(node, rawLines);
    if (table) return table;
    return {
        lines: visibleInlineText(node).split("\n"),
        placeholderLines: visibleInlineText(node, true).split("\n"),
    };
}

function parseCommitFooters(rawLines) {
    const root = new commonmark.Parser().parse(rawLines.join("\n"));
    const paragraphLines = new Set();
    for (let block = root.firstChild; block; block = block.next) {
        if (block.type !== "paragraph") continue;
        const start = block.sourcepos[0][0] - 1;
        const end = block.sourcepos[1][0] - 1;
        for (let i = start; i <= end; i++) paragraphLines.add(i);
    }
    const entries = [];
    let footerStart = rawLines.length,
        active = null;
    for (let i = 0; i < rawLines.length; i++) {
        const marker = paragraphLines.has(i)
            ? /^(BREAKING CHANGE|[A-Za-z][A-Za-z0-9-]*)(?:: +| +#)(.*)$/u.exec(
                  rawLines[i],
              )
            : null;
        if (footerStart === rawLines.length) {
            if (!marker || (i > 0 && rawLines[i - 1].trim())) continue;
            footerStart = i;
        }
        if (marker) {
            if (active) entries.push(active);
            active = { token: marker[1], start: i, content: [marker[2]] };
        } else if (active) active.content.push(rawLines[i]);
    }
    if (active) entries.push(active);
    return { entries, footerStart, paragraphLines };
}
function titleErrors(value) {
    const errors = [];
    if (typeof value !== "string" || !value.trim())
        return ["提交或 PR 标题为空"];
    if (value !== value.normalize("NFC"))
        errors.push("标题必须采用 NFC 规范化文本");
    if (hasInvisibleChars(value))
        errors.push("标题包含控制字符、非普通空格或不可见 Unicode 字符");
    const m =
        /^(feat|fix|docs|refactor|perf|test|build|ci|chore|style|revert)\(([a-z][a-z0-9]*(?:[-/][a-z0-9]+)*)\)(!)?: ([^\r\n]+)$/u.exec(
            value,
        );
    if (!m) return [...errors, "标题须采用 type(scope): 简体中文具体变更主题"];
    const subject = m[4];
    if (m[2].length > 36) errors.push("scope 过长");
    if (subject.length < 8 || subject.length > 105)
        errors.push("主题没有清晰的长度边界");
    if (subject !== subject.trim() || /\s{2,}/u.test(subject))
        errors.push("主题存在首尾或连续空白");
    if ((subject.match(/\p{Script=Han}/gu) || []).length < 4)
        errors.push("主题中文行为或对象描述不足");
    if (
        /^(?:更新|优化|修复|调整|完善|修改|改进|处理|整理)(?:项目|代码|文件|问题|功能|内容|配置|逻辑|文档|测试|流程|实现)?$/u.test(
            subject,
        )
    )
        errors.push("主题使用空泛描述");
    if (/\[(?:skip ci|ci skip)\]|\b(?:WIP|FIXME|TODO|TBD)\b/iu.test(subject))
        errors.push("主题含跳过检查或占位标记");
    return errors;
}

function commitErrors(message) {
    if (typeof message !== "string" || !message) return ["提交消息为空"];
    const lines = message.replace(/\r\n/gu, "\n").split("\n");
    const errors = titleErrors(lines[0]).map((e) => "提交：" + e);
    const rawBody = lines.slice(1).join("\n");
    const bodyLines = lines.slice(1);
    const rendered = visibleStructure(rawBody);
    const renderedLines = rendered.lines;
    const { entries, footerStart, paragraphLines } =
        parseCommitFooters(bodyLines);
    const footers = entries.filter(
        (f) => f.token === "BREAKING CHANGE" || f.token === "BREAKING-CHANGE",
    );
    const bodyBeforeFooters = bodyLines.slice(0, footerStart).join("\n");
    const visibleBody = visibleStructure(bodyBeforeFooters)
        .placeholderLines.join("\n")
        .trim();
    const m =
        /^(feat|fix|docs|refactor|perf|test|build|ci|chore|style|revert)\([^)]+\)(!)?: /u.exec(
            lines[0],
        );
    if (rawBody.trim() && lines[1] !== "")
        errors.push("提交标题与正文或 footer 必须以空行分隔");
    if (rawBody !== rawBody.normalize("NFC"))
        errors.push("提交正文必须采用 NFC 规范化文本");
    if (
        (rawBody && hasInvisibleChars(rawBody, true)) ||
        hasInvisibleChars(renderedLines.join("\n"), true)
    )
        errors.push("提交正文包含控制字符、非普通空格或不可见 Unicode 字符");
    if (m && /^(?:feat|fix|refactor|perf)$/u.test(m[1])) {
        if (lines[1] !== "" || visibleBody.replace(/\s/gu, "").length < 24)
            errors.push("实质功能或缺陷变更需要空行分隔的可见、有效正文");
    }
    if (
        visibleBody &&
        (visibleBody.match(/\p{Script=Han}/gu) || []).length < 4
    ) {
        errors.push("提交正文需要简体中文行为或影响说明");
    }
    if (rendered.placeholderLines.some(isPlaceholderLine))
        errors.push("提交正文包含未填写的占位内容");
    if (entries.some((f) => !f.content.join("\n").trim()))
        errors.push("提交 footer 必须包含非空值");
    const validBreakStarts = new Set(footers.map((f) => f.start));
    if (
        bodyLines.some(
            (line, i) =>
                paragraphLines.has(i) &&
                /^BREAKING(?: CHANGE|-CHANGE)[ \t]*:/u.test(line) &&
                !/^BREAKING(?: CHANGE|-CHANGE): /u.test(line),
        )
    )
        errors.push("不兼容变更 footer 须使用冒号及普通空格分隔");
    if (
        bodyLines.some(
            (line, i) =>
                paragraphLines.has(i) &&
                /^BREAKING(?: CHANGE|-CHANGE): /u.test(line) &&
                !validBreakStarts.has(i),
        )
    )
        errors.push("不兼容变更 footer 必须与正文以空行分隔");
    if ((m && m[2]) || footers.length) {
        const message = "不兼容变更必须具体说明契约、影响和迁移方式";
        // Conventional Commits 允许通过标题 ! 标记而不重复 BREAKING CHANGE footer。
        const explanations = footers.length
            ? footers.map((f) =>
                  visibleStructure(f.content.join("\n"))
                      .placeholderLines.join("\n")
                      .trim(),
              )
            : [visibleBody];
        for (const details of explanations) {
            // 固定关键词不能判断不同技术领域的迁移说明是否完整。
            if (details.replace(/\s/gu, "").length < 35) errors.push(message);
        }
    }
    return errors;
}

function visibleStructure(body, includeHeadings = true) {
    const root = parseBodyMarkdown(body);
    const rawLines = body.replace(/\r\n/gu, "\n").split("\n");
    const lines = [];
    const placeholderLines = [];
    const walker = root.walker();
    let event;
    while ((event = walker.next())) {
        if (!event.entering) continue;
        const node = event.node;
        if (!["paragraph", "html_block"].includes(node.type) &&
            !(includeHeadings && node.type === "heading")) continue;
        const visible = visibleBlockLines(node, rawLines);
        lines.push(...visible.lines);
        placeholderLines.push(...visible.placeholderLines);
    }
    return { lines, placeholderLines };
}

module.exports = { titleErrors, commitErrors, visibleStructure, isPlaceholderLine };

if (require.main === module) {
    try {
        const [mode, file, ...extra] = process.argv.slice(2);
        if (mode !== "message-file" || !file || extra.length) {
            throw new Error(
                "用法：node .github/scripts/commit_message.cjs message-file <消息文件>",
            );
        }
        const errors = commitErrors(fs.readFileSync(file, "utf8"));
        for (const error of errors) console.error(error);
        if (errors.length) process.exitCode = 1;
        else console.log("提交消息校验通过");
    } catch (error) {
        console.error(error.message);
        process.exitCode = 1;
    }
}
