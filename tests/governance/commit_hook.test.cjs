"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const { spawnSync } = require("node:child_process");
const test = require("node:test");

const root = path.resolve(__dirname, "../..");
const installer = path.join(root, "scripts/install_commit_hook.cjs");
const git = process.env.STAGESPIRIT_TEST_GIT || "git";
const environment = {
    ...process.env,
    GIT_CONFIG_NOSYSTEM: "1",
    GIT_CONFIG_GLOBAL: os.platform() === "win32" ? "NUL" : "/dev/null",
    GIT_AUTHOR_NAME: "StageSpirit Test",
    GIT_AUTHOR_EMAIL: "test@example.invalid",
    GIT_COMMITTER_NAME: "StageSpirit Test",
    GIT_COMMITTER_EMAIL: "test@example.invalid",
};

function repository(t) {
    const directory = fs.mkdtempSync(
        path.join(os.tmpdir(), "stagespirit-hook 中文 "),
    );
    t.after(() => fs.rmSync(directory, { recursive: true, force: true }));
    const result = spawnSync(git, ["init", "-b", "main", directory], {
        env: environment,
        encoding: "utf8",
    });
    assert.equal(result.status, 0, result.stderr);
    fs.cpSync(
        path.join(root, ".github/scripts"),
        path.join(directory, ".github/scripts"),
        { recursive: true },
    );
    return directory;
}

function install(directory) {
    return spawnSync(process.execPath, [installer, "--git-executable", git], {
        cwd: directory,
        env: environment,
        encoding: "utf8",
    });
}

test("installed hook validates real commits using its private copy", (t) => {
    const directory = repository(t);
    const preCommit = path.join(directory, ".git/hooks/pre-commit");
    fs.writeFileSync(preCommit, "#!/bin/sh\nexit 0\n", { mode: 0o755 });
    const result = install(directory);
    assert.equal(result.status, 0, result.stderr);
    assert.equal(fs.readFileSync(preCommit, "utf8"), "#!/bin/sh\nexit 0\n");
    fs.rmSync(path.join(directory, ".github"), {
        recursive: true,
        force: true,
    });
    fs.writeFileSync(path.join(directory, "sample.txt"), "synthetic content\n");
    const add = spawnSync(git, ["add", "--", "sample.txt"], {
        cwd: directory,
        env: environment,
        encoding: "utf8",
    });
    assert.equal(add.status, 0, add.stderr);
    const message = path.join(directory, ".git/test-message.txt");
    fs.writeFileSync(message, "feat: invalid title\n");
    const invalid = spawnSync(
        git,
        ["-c", "commit.gpgsign=false", "commit", "-F", message],
        { cwd: directory, env: environment, encoding: "utf8" },
    );
    assert.notEqual(invalid.status, 0);
    assert.match(invalid.stderr, /type\(scope\)/u);
    fs.writeFileSync(
        message,
        "feat(runtime): 增加合成样本用于钩子验证\n\n添加独立样本文件并检查提交钩子能读取消息，保留暂存内容且使用 Git 私有目录中的校验器。\n",
    );
    const valid = spawnSync(
        git,
        ["-c", "commit.gpgsign=false", "commit", "-F", message],
        { cwd: directory, env: environment, encoding: "utf8" },
    );
    assert.equal(valid.status, 0, valid.stderr);
});

test("preserve an existing independent commit-msg hook", (t) => {
    const directory = repository(t);
    const hook = path.join(directory, ".git/hooks/commit-msg");
    const content = "#!/bin/sh\nexit 0\n";
    fs.writeFileSync(hook, content, { mode: 0o755 });
    const result = install(directory);
    assert.equal(result.status, 1);
    assert.match(result.stderr, /独立 commit-msg/u);
    assert.equal(fs.readFileSync(hook, "utf8"), content);
});
