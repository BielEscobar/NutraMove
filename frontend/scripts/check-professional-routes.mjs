import assert from "node:assert/strict";
import { existsSync, readFileSync } from "node:fs";
import { join } from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

const root = fileURLToPath(new URL("../", import.meta.url));
const detail = readFileSync(
  join(root, "src/components/students/student-detail.tsx"),
  "utf8",
);
const routeRoot = join(root, "src/app/professional/students/[id]");
const interpolation = (name) => `${"$"}{${name}}`;

for (const segment of ["diets", "workouts", "evolution", "hydration"]) {
  test(`Student detail links to the existing ${segment} page`, () => {
    assert.ok(existsSync(join(routeRoot, segment, "page.tsx")));
    assert.ok(
      detail.includes(
        `href={\`/${interpolation("area")}/students/${interpolation("data.id")}/${segment}\`}`,
      ),
    );
  });
}

test("visible AI plan actions use Portuguese labels", () => {
  const generator = readFileSync(
    join(root, "src/components/ai/ai-plans-generator.tsx"),
    "utf8",
  );
  assert.match(generator, /kindLabels\[kind\]\.toLowerCase\(\)/);
  assert.doesNotMatch(generator, /Revisar \$\{kind\}|Ver \$\{kind\}/);
  assert.ok(
    existsSync(
      join(root, "src/app/professional/workout-versions/[id]/page.tsx"),
    ),
  );
  assert.match(
    generator,
    /href=\{`\/professional\/\$\{kind\}-versions\/\$\{plan\.id\}`\}/,
  );
  assert.doesNotMatch(generator, /\$\{editable \? "\/edit"/);
});

test("AI review opens version detail and unpublished details offer confirmed deletion", () => {
  const generator = readFileSync(
    join(root, "src/components/ai/ai-generator.tsx"),
    "utf8",
  );
  assert.doesNotMatch(generator, /\$\{result\.id\}\/edit/);
  for (const kind of ["diets", "workouts"]) {
    const version = readFileSync(
      join(root, `src/components/${kind}/version-detail.tsx`),
      "utf8",
    );
    assert.match(version, /Excluir este rascunho\?/);
    assert.match(version, /method: "DELETE"/);
    assert.match(version, /\["DRAFT", "PENDING_REVIEW"\]/);
  }
});
