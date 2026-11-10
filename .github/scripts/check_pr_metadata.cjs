"use strict";

const fs = require("node:fs");
const { titleErrors, commitErrors } = require("./commit_message.cjs");

function validatePullRequest(pullRequest, commits) {
    const errors = titleErrors(pullRequest.title).map(
        (error) => `PR 标题：${error}`,
    );
    if (commits.length !== pullRequest.commits || !commits.length) {
        errors.push("PR 提交列表不完整");
    }
    if (commits.at(-1)?.sha !== pullRequest.head.sha) {
        errors.push("PR 提交列表与当前 HEAD 不一致");
    }
    if (new Set(commits.map((item) => item.sha)).size !== commits.length) {
        errors.push("PR 提交列表包含重复记录");
    }
    for (const item of commits) {
        errors.push(
            ...commitErrors(item.commit.message).map(
                (error) => `${item.sha}: ${error}`,
            ),
        );
    }
    return errors;
}

async function checkPullRequest(
    event,
    { token, apiUrl = "https://api.github.com", fetchImpl = fetch },
) {
    const repository = event.repository?.full_name;
    const number = event.pull_request?.number;
    if (!/^[A-Za-z0-9_.-]+\/[A-Za-z0-9_.-]+$/u.test(repository || "")) {
        throw new Error("PR 仓库身份无效");
    }
    if (!Number.isSafeInteger(number) || number <= 0)
        throw new Error("PR 编号无效");
    if (!token) throw new Error("缺少 GitHub 读取令牌");
    const prefix = `/repos/${repository}/pulls/${number}`;

    async function read(path) {
        const response = await fetchImpl(new URL(path, apiUrl), {
            headers: {
                Accept: "application/vnd.github+json",
                Authorization: `Bearer ${token}`,
                "X-GitHub-Api-Version": "2022-11-28",
            },
        });
        if (!response.ok)
            throw new Error(`GitHub 元数据读取失败，HTTP ${response.status}`);
        return response.json();
    }

    const current = await read(prefix);
    if (
        current.head.sha !== event.pull_request.head.sha ||
        current.base.sha !== event.pull_request.base.sha
    ) {
        throw new Error("PR HEAD 或目标基线已改变，需要运行当前版本的检查");
    }
    const commits = [];
    for (let page = 1; ; page += 1) {
        const items = await read(`${prefix}/commits?per_page=100&page=${page}`);
        if (!Array.isArray(items)) throw new Error("PR 提交列表响应格式无效");
        commits.push(...items);
        if (items.length < 100) break;
    }
    const latest = await read(prefix);
    if (
        latest.head.sha !== current.head.sha ||
        latest.base.sha !== current.base.sha ||
        latest.title !== current.title
    ) {
        throw new Error("PR 在校验期间发生变化，需要重新检查");
    }
    return validatePullRequest(latest, commits);
}

module.exports = { checkPullRequest, validatePullRequest };

if (require.main === module) {
    Promise.resolve()
        .then(async () => {
            const event = JSON.parse(
                fs.readFileSync(process.env.GITHUB_EVENT_PATH, "utf8"),
            );
            const errors = await checkPullRequest(event, {
                token: process.env.GITHUB_TOKEN,
                apiUrl: process.env.GITHUB_API_URL || "https://api.github.com",
            });
            for (const error of errors) console.error(error);
            if (errors.length) process.exitCode = 1;
            else console.log("PR 标题和提交消息校验通过");
        })
        .catch((error) => {
            console.error(error.message);
            process.exitCode = 1;
        });
}
