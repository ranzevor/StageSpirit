"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const { spawnSync } = require("node:child_process");
const test = require("node:test");
const {
    titleErrors,
    commitErrors,
} = require("../../.github/scripts/commit_message.cjs");
const {
    checkPullRequest,
    validatePullRequest,
} = require("../../.github/scripts/check_pr_metadata.cjs");

const title = "feat(runtime): 建立独立标准输入输出运行入口";
const message = `${title}\n\n将运行配置与数据代际分别保存，并在重启时读取相同配置。新增跨进程实例互斥检查，验证重复启动的拒绝行为。\n`;

for (const invalid of [
    "feat: add isolated stdio runtime bootstrap (#1)",
    "建立独立 stdio MCP 运行入口 (#1)",
    "feat(runtime): add isolated stdio runtime bootstrap",
    "feat(Runtime): 建立独立标准输入输出运行入口",
    "feat(runtime): 更新",
    `${title}\u200b`,
]) {
    test(`reject title ${JSON.stringify(invalid)}`, () => {
        assert.ok(titleErrors(invalid).length);
    });
}

test("accept scoped Chinese title and substantive body", () => {
    assert.deepEqual(titleErrors(title), []);
    assert.deepEqual(commitErrors(message), []);
});

for (const body of [
    "",
    "TODO",
    "```text\n仅使用代码块填充功能提交正文无法说明实际变更及影响范围\n```",
    "`使用行内代码填充功能提交正文无法说明实际变更及影响范围`",
]) {
    test(`reject ineffective body ${JSON.stringify(body)}`, () => {
        assert.ok(commitErrors(`${title}\n\n${body}`).length);
    });
}

test("message-file CLI checks UTF-8 files in paths containing spaces", (t) => {
    const directory = fs.mkdtempSync(
        path.join(os.tmpdir(), "stagespirit 中文 "),
    );
    t.after(() => fs.rmSync(directory, { recursive: true, force: true }));
    const file = path.join(directory, "提交 消息.txt");
    const script = path.resolve(
        __dirname,
        "../../.github/scripts/commit_message.cjs",
    );
    fs.writeFileSync(file, message, "utf8");
    const valid = spawnSync(process.execPath, [script, "message-file", file], {
        encoding: "utf8",
    });
    assert.equal(valid.status, 0, valid.stderr);
    fs.writeFileSync(file, "feat: invalid title\n", "utf8");
    const invalid = spawnSync(
        process.execPath,
        [script, "message-file", file],
        { encoding: "utf8" },
    );
    assert.equal(invalid.status, 1);
    assert.match(invalid.stderr, /type\(scope\)/u);
});

const pullRequest = {
    title,
    commits: 102,
    head: { sha: "head-102" },
    base: { sha: "base-1" },
};
const commits = Array.from({ length: 102 }, (_, index) => ({
    sha: index === 101 ? "head-102" : `commit-${index}`,
    commit: { message },
}));
const event = {
    repository: { full_name: "test/stagespirit" },
    pull_request: { ...pullRequest, number: 2 },
};

function client(responses) {
    const calls = [];
    return {
        calls,
        fetchImpl: async (url) => {
            calls.push(url.pathname + url.search);
            assert.ok(responses.length, "unexpected API request");
            return { ok: true, json: async () => responses.shift() };
        },
    };
}

test("read every commit page and recheck current PR metadata", async () => {
    const request = client([
        pullRequest,
        commits.slice(0, 100),
        commits.slice(100),
        pullRequest,
    ]);
    const errors = await checkPullRequest(event, {
        token: "synthetic-token",
        fetchImpl: request.fetchImpl,
    });
    assert.deepEqual(errors, []);
    assert.deepEqual(request.calls, [
        "/repos/test/stagespirit/pulls/2",
        "/repos/test/stagespirit/pulls/2/commits?per_page=100&page=1",
        "/repos/test/stagespirit/pulls/2/commits?per_page=100&page=2",
        "/repos/test/stagespirit/pulls/2",
    ]);
});

test("reject incomplete commit list", () => {
    assert.ok(
        validatePullRequest(pullRequest, commits.slice(1)).includes(
            "PR 提交列表不完整",
        ),
    );
});

test("reject invalid source commit even when PR title is valid", () => {
    const changed = [
        { ...commits[0], commit: { message: "feat: invalid title" } },
        ...commits.slice(1),
    ];
    assert.ok(validatePullRequest(pullRequest, changed).length);
});

test("reject stale head before reading commits", async () => {
    const request = client([{ ...pullRequest, head: { sha: "new-head" } }]);
    await assert.rejects(
        checkPullRequest(event, {
            token: "synthetic-token",
            fetchImpl: request.fetchImpl,
        }),
        /HEAD/u,
    );
    assert.equal(request.calls.length, 1);
});

test("reject title change during validation", async () => {
    const request = client([
        pullRequest,
        commits.slice(0, 100),
        commits.slice(100),
        { ...pullRequest, title: "changed" },
    ]);
    await assert.rejects(
        checkPullRequest(event, {
            token: "synthetic-token",
            fetchImpl: request.fetchImpl,
        }),
        /校验期间/u,
    );
});

test("report API failure without credential content", async () => {
    await assert.rejects(
        checkPullRequest(event, {
            token: "synthetic-secret",
            fetchImpl: async () => ({ ok: false, status: 403 }),
        }),
        (error) =>
            error.message.includes("403") &&
            !error.message.includes("synthetic-secret"),
    );
});

test("reject English-only explanatory body", () => {
    const invalid = `${title}\n\nAdd the runtime configuration and persist the current generation between restarts.`;
    assert.ok(
        commitErrors(invalid).includes("提交正文需要简体中文行为或影响说明"),
    );
});

test("reject duplicated commit page records", () => {
    const repeated = [commits[0], commits[0], ...commits.slice(2)];
    assert.ok(
        validatePullRequest(pullRequest, repeated).includes(
            "PR 提交列表包含重复记录",
        ),
    );
});
