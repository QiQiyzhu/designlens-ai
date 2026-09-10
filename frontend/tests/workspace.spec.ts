import { test, expect, type Page } from "@playwright/test";

const nav = (page: Page, name: string) =>
  page
    .getByRole("navigation")
    .getByRole("button", { name: new RegExp(name) })
    .click();
const shot = async (page: Page, name: string) => {
  await page.evaluate(() => window.scrollTo(0, 0));
  return page.screenshot({ path: `../docs/screenshots/${name}.png`, fullPage: true });
};

test.beforeEach(async ({ page }) => {
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await page.goto("/");
  await expect(
    page.getByRole("button", { name: "Find signals" }),
  ).toBeVisible();
  await expect(
    page.getByText("Onboarding", { exact: true }).first(),
  ).toBeVisible();
  expect(errors).toEqual([]);
});

test("original evidence is one click away and modal keyboard focus stays contained", async ({
  page,
}) => {
  await shot(page, "research-dashboard");
  await page.getByRole("button", { name: /^Onboarding/ }).click();
  const dialog = page.getByRole("dialog", { name: "Original evidence" });
  await expect(
    dialog.getByText("SYNTHETIC SCENARIO:", { exact: false }).first(),
  ).toBeVisible();
  await expect(
    dialog.getByText("DEMO / SYNTHETIC", { exact: true }),
  ).toBeVisible();
  await expect(dialog.getByText("Provenance", { exact: true })).toBeVisible();
  await shot(page, "evidence-insight");
  await page.keyboard.press("Tab");
  await expect(
    dialog.getByRole("button", { name: "Close evidence" }),
  ).toBeFocused();
  await page.keyboard.press("Escape");
  await expect(dialog).not.toBeVisible();
  await expect(page.getByRole("button", { name: /^Onboarding/ })).toBeFocused();
});

test("invalid import is recoverable; CSV import persists exact source and can generate reviewed extracts", async ({
  page,
}) => {
  await page.getByRole("button", { name: "Add evidence" }).click();
  const dialog = page.getByRole("dialog", { name: "Import evidence" });
  await dialog.getByLabel("Filename", { exact: true }).fill("fixture.json");
  await dialog.getByLabel("Content", { exact: true }).fill("{broken");
  await dialog.getByRole("button", { name: "Preview local cleanup" }).click();
  await expect(dialog.getByRole("alert")).toBeVisible();
  await expect(dialog.getByLabel("Content", { exact: true })).toHaveValue(
    "{broken",
  );
  await dialog.getByLabel("Filename", { exact: true }).fill("fixture.csv");
  await dialog
    .getByLabel("Content", { exact: true })
    .fill(
      'content,participant,segment\n"SYNTHETIC: route labels should explain a key cost.",Browser fixture,Route QA',
    );
  await dialog.getByRole("button", { name: "Preview local cleanup" }).click();
  await dialog.getByLabel("I reviewed the cleaned content and remaining identifiers").check();
  await dialog.getByRole("button", { name: "Import reviewed copy" }).click();
  await expect(dialog).not.toBeVisible();
  await page.getByRole("button", { name: /^Route QA/ }).click();
  await expect(
    page
      .getByRole("dialog")
      .getByText("SYNTHETIC: route labels should explain a key cost.", {
        exact: true,
      }),
  ).toBeVisible();
  await page.keyboard.press("Escape");
  const row = page
    .getByRole("row")
    .filter({ has: page.getByRole("button", { name: /^Route QA/ }) });
  await row.getByRole("checkbox").check();
  await page.getByRole("button", { name: "Find signals" }).click();
  await expect(
    page.getByText("Observation · Route QA", { exact: true }),
  ).toBeVisible();
});

test("human-reviewed evidence becomes a scored opportunity, a No AI canvas and a planned protocol", async ({
  page,
}) => {
  await page
    .locator(".insight")
    .first()
    .getByRole("button", { name: "Accept", exact: true })
    .click();
  let dialog = page.getByRole("dialog");
  await dialog
    .getByLabel("Review note")
    .fill(
      "Synthetic hypothesis only; exact excerpt checked. Real participant validation remains pending.",
    );
  await dialog.getByRole("button", { name: "Save decision" }).click();
  await expect(dialog).not.toBeVisible();
  await nav(page, "Opportunities");
  await page.getByRole("button", { name: "New opportunity" }).click();
  dialog = page.getByRole("dialog");
  await dialog
    .getByLabel("Title", { exact: true })
    .fill("Clarify resonance before a build choice");
  await dialog
    .getByLabel("Problem to solve")
    .fill(
      "Synthetic task: the current label may not explain the effect; investigate with real players.",
    );
  await dialog.getByLabel("MoSCoW priority").selectOption("Should");
  await dialog.getByRole("button", { name: "Save decision" }).click();
  await expect(dialog).not.toBeVisible();
  await expect(
    page.getByRole("button", { name: "Plan experiment", exact: true }),
  ).toBeDisabled();
  await page.getByRole("button", { name: "Review priority" }).click();
  dialog = page.getByRole("dialog");
  await dialog
    .getByLabel("Reason", { exact: true })
    .fill("Confirm the demonstration protocol, not a validated user demand.");
  await dialog.getByRole("button", { name: "Save decision" }).click();
  await expect(dialog).not.toBeVisible();
  await shot(page, "opportunity-map");
  await page.getByRole("button", { name: "Compare approaches" }).click();
  await page
    .getByRole("button", { name: "Compare approaches", exact: true })
    .click();
  await expect(
    page
      .locator(".recommendation")
      .getByRole("heading", { name: "No AI", exact: true }),
  ).toBeVisible();
  await expect(
    page.getByText("Non-AI alternative", { exact: true }),
  ).toBeVisible();
  await shot(page, "feasibility-canvas");
  await nav(page, "Opportunities");
  await page
    .getByRole("button", { name: "Plan experiment", exact: true })
    .click();
  dialog = page.getByRole("dialog");
  await dialog
    .getByLabel("Experiment title")
    .fill("Context labels qualitative pilot");
  await dialog
    .getByLabel("Hypothesis", { exact: true })
    .fill("A clearer contextual label may improve unaided task understanding.");
  await dialog
    .getByLabel("Primary metric")
    .fill("Unaided task completion under predefined rubric");
  await dialog
    .getByLabel("Decision rule and limitations")
    .fill(
      "Continue only if observed critical errors decline without a new critical misunderstanding; no significance claim.",
    );
  await dialog.getByRole("button", { name: "Save decision" }).click();
  await expect(dialog).not.toBeVisible();
  await page
    .getByText("Context labels qualitative pilot · planned", { exact: true })
    .click();
  await expect(
    page.getByText("No result has been recorded.", { exact: false }),
  ).toBeVisible();
});

test("workflow nodes and prompts version independently; diff, approval and pinned trace are usable", async ({
  page,
}) => {
  await nav(page, "Workflows");
  await expect(page.locator(".workflow-nodes .node")).toHaveCount(7);
  await page
    .getByRole("button", { name: "Prompt registry", exact: true })
    .click();
  const registry = page.locator(".prompt-registry");
  await expect(registry.getByLabel("Prompt template")).toContainText(
    "Return claims",
  );
  await registry
    .getByLabel("Prompt goal")
    .fill("Reviewed evidence extraction with visible counterexamples");
  await registry
    .getByLabel("Prompt template")
    .fill(
      "Task: {{input}}\nSource data: {{context}}\nReturn exact extracts with source IDs. Preserve counterexamples; abstain without evidence.",
    );
  await registry.getByRole("button", { name: "Save prompt version" }).click();
  await expect(registry.getByLabel("Inspect prompt version")).toHaveValue("3");
  await page
    .getByLabel("Prompt version pinned to this workflow")
    .selectOption("3");
  await page
    .getByLabel("Workflow name", { exact: true })
    .fill("Evidence pipeline reviewed");
  await page.getByRole("button", { name: "Save workflow version" }).click();
  await expect(page.getByText("Saved v2", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Show diff" }).click();
  await expect(page.getByLabel("Version diff")).toContainText(
    "Evidence pipeline reviewed",
  );
  await page.getByRole("button", { name: "Close prompt registry" }).click();
  await page.getByLabel("Research question", { exact: true }).fill("resonance");
  await page.getByRole("button", { name: "Run workflow", exact: true }).click();
  await expect(
    page.getByText("Human approval required", { exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Approve & continue" }),
  ).toBeDisabled();
  await shot(page, "workflow-builder");
  await page
    .getByLabel("Approval review note")
    .fill("I reviewed the exact synthetic source and its limited scope.");
  await page.getByRole("button", { name: "Approve & continue" }).click();
  await expect(page.locator(".run-summary .tag")).toHaveText("completed");
  await expect(
    page.getByText("Workflow v2 · Prompt v3", { exact: true }),
  ).toBeVisible();
});

test("evaluation shows actual failed cases and records an explicit human rating", async ({
  page,
}) => {
  await nav(page, "Evaluation");
  await page.getByRole("button", { name: "Run comparison" }).click();
  await expect(
    page.getByRole("heading", { name: "Variant comparison" }),
  ).toBeVisible();
  const baseline = page
    .locator(".comparison-table tr")
    .filter({ hasText: "Prompt V1" });
  await expect(baseline).toContainText("0 / 12");
  await expect(
    page.getByText("48 executed cases across variants", { exact: false }),
  ).toBeVisible();
  await page.getByLabel("Failed only").check();
  await expect(page.getByText("Rules failed", { exact: true })).toBeVisible();
  await page
    .getByLabel("Human rating rationale")
    .fill(
      "The plain output has no source IDs and cannot support a reviewable decision.",
    );
  await page.getByLabel("Usefulness rating").selectOption("1");
  await page.getByRole("button", { name: "Save human rating" }).click();
  await expect(
    page.getByText("Reviewed: 1 / 5", { exact: false }),
  ).toBeVisible();
  await shot(page, "evaluation-dashboard");
});

test("analytics keeps synthetic cohorts separate and narrow layouts stay usable", async ({
  page,
}) => {
  await nav(page, "Analytics");
  await expect(
    page.getByRole("heading", { name: "Weekly validated product decisions" }),
  ).toBeVisible();
  await expect(page.locator(".northstar-value")).toContainText("0");
  await page.getByLabel("Cohort", { exact: true }).selectOption("real");
  await expect(
    page.getByText("No events in this cohort.", { exact: true }),
  ).toBeVisible();
  await expect(
    page.getByText("No eligible data", { exact: true }).first(),
  ).toBeVisible();
  await page.getByLabel("Cohort", { exact: true }).selectOption("demo");
  await shot(page, "analytics-dashboard");
  await page.setViewportSize({ width: 390, height: 844 });
  await nav(page, "Research");
  await expect(
    page.getByRole("button", { name: "Add evidence" }),
  ).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth + 1,
    ),
  ).toBeTruthy();
  await shot(page, "research-mobile");
});

test("local privacy preview invalidates edited input and sharing can be approved then revoked", async ({ page }) => {
  await page.getByRole("button", { name: "Add evidence" }).click();
  const dialog = page.getByRole("dialog", { name: "Import evidence" });
  await dialog.getByLabel("Filename", { exact: true }).fill("privacy-qa.txt");
  await dialog.getByLabel("Source / participant", { exact: true }).fill("Alex Demo");
  await dialog.getByLabel("Segment", { exact: true }).fill("Privacy intake QA");
  await dialog.getByLabel("Content", { exact: true }).fill("SYNTHETIC QA ONLY: Alex Demo finds the route map unclear. Email alex@example.invalid or call +1 (415) 555-0100.");
  await dialog.getByLabel("Names or phrases to remove · one per line", { exact: true }).fill("Alex Demo");
  await dialog.getByLabel("This is real research data").check();
  await dialog.getByLabel("Consent to collect and retain this research has been confirmed").check();
  await dialog.getByRole("button", { name: "Preview local cleanup" }).click();
  let preview = dialog.getByRole("region", { name: "Cleaned source preview" });
  await expect(preview).toContainText("[EMAIL]");
  await expect(preview).toContainText("[PHONE]");
  await expect(preview).not.toContainText("alex@example.invalid");
  await dialog.getByLabel("I reviewed the cleaned content and remaining identifiers").check();
  await dialog.getByLabel("Segment", { exact: true }).fill("Privacy intake QA revised");
  await expect(preview).not.toBeVisible();
  await expect(dialog.getByRole("button", { name: "Preview local cleanup" })).toBeVisible();
  await dialog.getByRole("button", { name: "Preview local cleanup" }).click();
  preview = dialog.getByRole("region", { name: "Cleaned source preview" });
  await expect(dialog.getByRole("button", { name: "Import reviewed copy" })).toBeDisabled();
  await dialog.getByLabel("I reviewed the cleaned content and remaining identifiers").check();
  await page.setViewportSize({ width: 390, height: 844 });
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1)).toBeTruthy();
  await dialog.getByRole("button", { name: "Import reviewed copy" }).scrollIntoViewIfNeeded();
  await page.screenshot({ path: "../docs/screenshots/privacy-preview-mobile.png", fullPage: false });
  await dialog.getByRole("button", { name: "Import reviewed copy" }).click();
  await expect(dialog).not.toBeVisible();
  await page.setViewportSize({ width: 1440, height: 1024 });
  await page.getByRole("button", { name: /^Privacy intake QA revised/ }).click();
  const source = page.getByRole("dialog", { name: "Original evidence" });
  await expect(source.getByRole("heading", { name: "Local-only research source" })).toBeVisible();
  await expect(source).not.toContainText("alex@example.invalid");
  await source.getByLabel("Sharing review note").fill("Scripted synthetic QA of consent UI; not a real participant review.");
  await source.getByLabel("I have authorization to share this cleaned source with the configured model service").check();
  await source.getByRole("button", { name: "Approve this source for cloud use" }).click();
  await expect(source.getByRole("heading", { name: "Reviewed cloud use approved" })).toBeVisible();
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.screenshot({ path: "../docs/screenshots/privacy-source-review.png", fullPage: false });
  await source.getByLabel("Sharing review note").fill("Scripted QA: withdraw permission for any future remote use.");
  await source.getByRole("button", { name: "Revoke future cloud use" }).click();
  await expect(source.getByRole("heading", { name: "Local-only research source" })).toBeVisible();
  await page.keyboard.press("Escape");
});
