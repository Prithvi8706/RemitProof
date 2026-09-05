import assert from "node:assert/strict";
import test from "node:test";
import { describeProposalOnlyOutcome, describeRemitProofOutcome } from "./case-comparison.ts";

const base = {
  llm_only_decision: "resolve",
  llm_only_wrong_resolution: false,
  expected_should_resolve: true,
  remitproof_decision: "resolved",
  remitproof_correct_resolution: true,
  correct_abstention: false,
  false_escalation: false,
  wrong_auto_resolution: false,
};

test("labels a proposal-only abstention on a resolvable case as a miss", () => {
  assert.deepEqual(
    describeProposalOnlyOutcome({ ...base, llm_only_decision: "abstain" }),
    {
      decision: "Abstain",
      verdict: "Missed resolvable exception",
      tone: "warning",
    },
  );
});

test("labels a RemitProof wrong auto-resolution as unsafe", () => {
  assert.deepEqual(
    describeRemitProofOutcome({
      ...base,
      remitproof_correct_resolution: false,
      wrong_auto_resolution: true,
    }),
    {
      decision: "Unsafe resolution",
      verdict: "Wrong automatic resolution",
      tone: "danger",
    },
  );
});
