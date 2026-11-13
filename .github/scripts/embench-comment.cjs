"use strict";

const MARKER = "<!-- rv32-embench-score -->";
const SHA = /^[0-9a-f]{40}$/;

function validateScore(value) {
  if (!value || value.schema !== 1 || value.baseline_branch !== "main" ||
      !SHA.test(value.candidate_sha) || !SHA.test(value.baseline_sha) ||
      !["ci", "full"].includes(value.workload) ||
      !["complete", "incomplete"].includes(value.status) ||
      !Array.isArray(value.profiles) || value.profiles.length > 256 ||
      !Number.isInteger(value.expected_profiles) || value.expected_profiles < 1 || value.expected_profiles > 256) {
    throw new Error("Invalid Embench score document");
  }
  if (value.pull_request_number != null && (!Number.isSafeInteger(value.pull_request_number) || value.pull_request_number < 1)) {
    throw new Error("Invalid pull request number");
  }
  const names = new Set();
  for (const row of value.profiles) {
    if (!/^rv32[a-z0-9_]{0,100}$/.test(row.profile) || names.has(row.profile) ||
        !Number.isInteger(row.programs) || row.programs < 1 || row.programs > 1000 ||
        ![row.base_score_per_mhz, row.head_score_per_mhz, row.relative_index].every(n => Number.isFinite(n) && n > 0) ||
        !Number.isFinite(row.delta_percent) ||
        Math.abs(row.delta_percent - (row.relative_index - 100)) > 1e-6 ||
        Math.abs(row.relative_index - 100 * row.head_score_per_mhz / row.base_score_per_mhz) > Math.max(1e-6, row.relative_index * 1e-6)) {
      throw new Error("Invalid Embench profile score");
    }
    names.add(row.profile);
  }
  if (value.status === "complete") {
    const geometric = Math.exp(value.profiles.reduce((sum, row) => sum + Math.log(row.relative_index), 0) / value.profiles.length);
    const baseMean = Math.exp(value.profiles.reduce((sum, row) => sum + Math.log(row.base_score_per_mhz), 0) / value.profiles.length);
    const headMean = Math.exp(value.profiles.reduce((sum, row) => sum + Math.log(row.head_score_per_mhz), 0) / value.profiles.length);
    if (![value.base_score_per_mhz, value.head_score_per_mhz].every(n => Number.isFinite(n) && n > 0) ||
        Math.abs(value.base_score_per_mhz - baseMean) > Math.max(1e-9, baseMean * 1e-6) ||
        Math.abs(value.head_score_per_mhz - headMean) > Math.max(1e-9, headMean * 1e-6) ||
        value.profiles.length !== value.expected_profiles ||
        !Number.isFinite(value.relative_index) || value.relative_index <= 0 ||
        !Number.isFinite(value.delta_percent) ||
        Math.abs(value.relative_index - geometric) > Math.max(1e-6, geometric * 1e-6) ||
        Math.abs(value.delta_percent - (value.relative_index - 100)) > 1e-6) {
      throw new Error("Invalid overall Embench score");
    }
  }
  return value;
}

function bodyFor(run, pr, score) {
  const completed = run.status === "completed";
  const success = completed && run.conclusion === "success" && score?.status === "complete";
  const lines = [MARKER, `<!-- embench-run:${run.id} -->`, `<!-- embench-phase:${completed ? "completed" : "running"} -->`, "### 🧪 Embench benchmark", ""];
  if (!completed) {
    lines.push("⏳ **Running** — this benchmark is informational and does not need to finish before merging.");
  } else if (!success) {
    lines.push("⚠️ **Score unavailable or incomplete.** No total is reported until every expected profile/program has compatible, verified results.");
  } else {
    const change = `${score.delta_percent >= 0 ? "+" : ""}${score.delta_percent.toFixed(2)}%`;
    const units = score.workload === "ci" ? "CI index/MHz" : "Embench/MHz";
    lines.push(`**Overall score: ${score.head_score_per_mhz.toFixed(5)} ${units}** · main: **${score.base_score_per_mhz.toFixed(5)}**`, "",
      `**Overall index: ${score.relative_index.toFixed(2)}** · **main = 100** · **${change}**`, "",
      `Candidate \`${score.candidate_sha.slice(0, 12)}\` versus **main** \`${score.baseline_sha.slice(0, 12)}\` (main frozen at run start).`, "",
      "| CPU profile | main score/MHz | PR score/MHz | Speed change |", "|---|---:|---:|---:|");
    for (const row of score.profiles) {
      lines.push(`| \`${row.profile}\` | ${row.base_score_per_mhz.toFixed(5)} | ${row.head_score_per_mhz.toFixed(5)} | ${row.delta_percent >= 0 ? "+" : ""}${row.delta_percent.toFixed(2)}% |`);
    }
    lines.push("", "Higher is faster. The overall index is the geometric mean of main/PR cycle ratios, with equal program weight within each profile and equal profile weight.",
      score.workload === "ci" ? "The shortened workload gives a **CI index**, not an official full Embench result. Scores come from simulation, not measured FPGA frequency/MIPS." : "Full Embench workload; simulation does not measure FPGA frequency/MIPS.");
  }
  if (completed && pr.state === "closed") lines.push("", pr.merged ? "This benchmark finished after the PR was merged." : "This benchmark finished after the PR was closed.");
  lines.push("", `[Full tables, logs and benchmark artifacts](${run.html_url}).`, "Main measurements are cached by processor inputs and measurement contract; changed inputs invalidate the cache.");
  return lines.join("\n");
}

async function publish({github, context, core, score = null}) {
  const run = context.payload.workflow_run;
  if (run.event !== "pull_request" || (run.repository?.full_name || context.payload.repository?.full_name) !== `${context.repo.owner}/${context.repo.repo}`) return;
  if (score) validateScore(score);
  let associated = run.pull_requests || [];
  if (!associated.length) {
    associated = (await github.rest.repos.listPullRequestsAssociatedWithCommit({...context.repo, commit_sha: run.head_sha, per_page: 100})).data;
  }
  // GitHub's commit-association endpoint omits some closed, unmerged PRs.
  // A recorded number is only a hint: pulls.get must still prove the repo and
  // exact workflow head SHA before any write is allowed.
  if (!associated.length && score?.pull_request_number) {
    associated = [{number: score.pull_request_number}];
  }
  const allowed = new Set([run.head_sha, ...(run.pull_requests || []).map(pr => pr.head?.sha)].filter(Boolean));
  if (score && !allowed.has(score.candidate_sha)) throw new Error("Score does not belong to this workflow's PR head");
  for (const item of associated.slice(0, 20)) {
    const pr = (await github.rest.pulls.get({...context.repo, pull_number: item.number})).data;
    if (pr.base.repo.full_name !== `${context.repo.owner}/${context.repo.repo}` || !allowed.has(pr.head.sha) || (score && pr.head.sha !== score.candidate_sha)) {
      core.info("Skipping stale or unrelated PR benchmark result");
      continue;
    }
    const comments = await github.paginate(github.rest.issues.listComments, {...context.repo, issue_number: pr.number, per_page: 100});
    const existing = comments.find(comment => comment.user?.login === "github-actions[bot]" && comment.user?.type === "Bot" && comment.body?.includes(MARKER));
    const previousRun = existing?.body.match(/<!-- embench-run:(\d+) -->/);
    if (previousRun && BigInt(previousRun[1]) > BigInt(run.id)) continue;
    if (previousRun && BigInt(previousRun[1]) === BigInt(run.id) && run.status !== "completed" && existing.body.includes("<!-- embench-phase:completed -->")) continue;
    const body = bodyFor(run, pr, score);
    if (existing) await github.rest.issues.updateComment({...context.repo, comment_id: existing.id, body});
    else await github.rest.issues.createComment({...context.repo, issue_number: pr.number, body});
  }
}

module.exports = {validateScore, bodyFor, publish};
