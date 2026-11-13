"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const {validateScore, bodyFor, publish, eligibleMainUpdate} = require("./embench-comment.cjs");
const sha = "a".repeat(40), base = "b".repeat(40);
function score() {
  return {schema: 1, status: "complete", baseline_branch: "main", baseline_sha: base,
    candidate_sha: sha, workload: "ci", expected_profiles: 1, relative_index: 200,
    delta_percent: 100, base_score_per_mhz: 1, head_score_per_mhz: 2, profiles: [{profile: "rv32im", programs: 22,
      base_score_per_mhz: 1, head_score_per_mhz: 2, relative_index: 200, delta_percent: 100}]};
}
function setup({state = "closed", merged = true, head = "c".repeat(40), merge = sha, comments = [], runId = 3} = {}) {
  const run = {id: runId, event: "push", head_branch: "main", status: "completed", conclusion: "success", head_sha: sha,
    repository: {full_name: "insper-riscv/Insper-RISC-V"},
    pull_requests: [{number: 7, head: {sha}}], html_url: "https://github.com/insper-riscv/Insper-RISC-V/actions/runs/3"};
  const pr = {number: 7, state, merged, merge_commit_sha: merge, head: {sha: head}, base: {ref: "main", repo: {full_name: "insper-riscv/Insper-RISC-V"}}};
  const writes = [];
  const github = {paginate: async () => comments, rest: {
    pulls: {get: async () => ({data: pr})},
    issues: {listComments() {}, createComment: async value => writes.push(value), updateComment: async value => writes.push(value)},
    repos: {listPullRequestsAssociatedWithCommit: async () => ({data: [pr]})}
  }};
  return {run, pr, writes, github, context: {ref: "refs/heads/main", eventName: "push", sha, repo: {owner: "insper-riscv", repo: "Insper-RISC-V"}, payload: {workflow_run: run}}, core: {info() {}}};
}

test("validates and renders normalized score and main comparison", () => {
  const value = validateScore(score());
  const {run, pr} = setup();
  const body = bodyFor(run, pr, value);
  assert.match(body, /Overall index: 200.00/);
  assert.match(body, /Overall score: 2.00000 CI index/);
  assert.match(body, /main = 100/);
  assert.match(body, /\+100.00%/);
  assert.match(body, /rv32im/);
  assert.match(body, /not an official full Embench/);
});
test("rejects injected labels, NaN, forged aggregate and inconsistent ratios", () => {
  for (const edit of [x => x.profiles[0].profile = "[link](evil)", x => x.relative_index = NaN,
    x => x.delta_percent = 10, x => x.profiles[0].head_score_per_mhz = 100,
    x => x.candidate_sha = "$(unsafe)", x => x.expected_profiles = 2]) {
    const value = score(); edit(value); assert.throws(() => validateScore(value));
  }
});
test("updates the bot comment rather than duplicating it, including after merge", async () => {
  const state = setup({state: "closed", merged: true, comments: [{id: 9, user: {login: "github-actions[bot]", type: "Bot"}, body: "<!-- rv32-embench-score -->\n<!-- embench-run:2 -->"}]});
  await publish({...state, score: score()});
  assert.equal(state.writes.length, 1); assert.equal(state.writes[0].comment_id, 9);
  assert.match(state.writes[0].body, /finished after the PR was merged/);
});
test("skips unrelated merge commits and older runs", async () => {
  for (const state of [setup({merge: "c".repeat(40)}), setup({comments: [{id: 9, user: {login: "github-actions[bot]", type: "Bot"}, body: "<!-- rv32-embench-score -->\n<!-- embench-run:99 -->"}]})]) {
    await publish({...state, score: score()}); assert.equal(state.writes.length, 0);
  }
});
test("never copies an artifact's unrelated SHA into a PR", async () => {
  const state = setup(), value = score(); value.candidate_sha = "c".repeat(40);
  await assert.rejects(publish({...state, score: value})); assert.equal(state.writes.length, 0);
});
test("running and failed benchmarks never advertise a complete score", () => {
  const {run, pr} = setup(); run.status = "in_progress";
  assert.match(bodyFor(run, pr, null), /Running after merge/);
  run.status = "completed"; run.conclusion = "failure";
  assert.match(bodyFor(run, pr, score()), /Score unavailable or incomplete/);
  assert.doesNotMatch(bodyFor(run, pr, score()), /Overall index: 200/);
});
test("an unrelated merge commit cannot receive an old failure", async () => {
  const state = setup({merge: "c".repeat(40)}); state.run.pull_requests = []; state.run.conclusion = "failure";
  await publish({...state, score: null}); assert.equal(state.writes.length, 0);
});

test("never posts a main result on an unmerged PR", async () => {
  const state = setup({state: "closed", merged: false});
  await publish({...state, score: score()});
  assert.equal(state.writes.length, 0);
});


test("a delayed running event never replaces the same run's final score", async () => {
  const state = setup({comments: [{id: 9, user: {login: "github-actions[bot]", type: "Bot"},
    body: "<!-- rv32-embench-score -->\n<!-- embench-run:3 -->\n<!-- embench-phase:completed -->"}]});
  state.run.status = "in_progress";
  await publish({...state, score: null});
  assert.equal(state.writes.length, 0);
});

test("PR runs and non-main runs cannot publish comments", async () => {
  for (const edit of [x => x.run.event = "pull_request", x => x.run.head_branch = "feature",
    x => x.run.repository.full_name = "fork/repo", x => x.pr.base.ref = "feature"]) {
    const state = setup(); edit(state);
    await publish({...state, score: score()});
    assert.equal(state.writes.length, 0);
  }
});

test("merge eligibility uses the resulting main commit, not the PR head", async () => {
  const state = setup();
  const outputs = {};
  state.core.setOutput = (key, value) => outputs[key] = value;
  state.github.paginate = async () => [state.pr];
  await eligibleMainUpdate(state);
  assert.deepEqual(outputs, {run: "true", pr: "7"});
  assert.notEqual(state.pr.head.sha, state.run.head_sha);
});

test("direct pushes and PR activity do not schedule a benchmark", async () => {
  for (const edit of [x => x.pr.merged = false, x => x.pr.merge_commit_sha = base,
    x => x.context.eventName = "pull_request", x => x.context.ref = "refs/heads/feature"]) {
    const state = setup(), outputs = {}; edit(state);
    state.core.setOutput = (key, value) => outputs[key] = value;
    state.github.paginate = async () => [state.pr];
    await eligibleMainUpdate(state);
    assert.equal(outputs.run, "false");
  }
});

test("manual benchmarks are allowed only for main", async () => {
  for (const ref of ["refs/heads/main", "refs/heads/feature"]) {
    const state = setup(), outputs = {};
    state.context.eventName = "workflow_dispatch";
    state.context.ref = ref;
    state.core.setOutput = (key, value) => outputs[key] = value;
    await eligibleMainUpdate(state);
    assert.equal(outputs.run, ref.endsWith("/main") ? "true" : "false");
  }
});
