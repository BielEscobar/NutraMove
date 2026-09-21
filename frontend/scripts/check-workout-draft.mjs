import assert from "node:assert/strict";
import test from "node:test";
import { clean, hasUnsavedChanges, hydrate } from "../src/lib/workout-draft.ts";

const received = {
  name: "Treino recebido da API",
  goal: null,
  frequency_per_week: 5,
  start_date: null,
  next_review_date: null,
  notes: null,
  days: [
    {
      name: "Segunda",
      description: null,
      isRest: false,
      exercises: [
        {
          name: "Agachamento",
          muscle_group: null,
          description: null,
          instructions: null,
          sets: 3,
          repetitions: "12",
          load: null,
          duration: null,
          rest_seconds: 60,
          notes: null,
        },
      ],
    },
  ],
};

test("API workout loads clean and becomes dirty only after a real edit", () => {
  const draft = hydrate(received);
  const saved = JSON.stringify(clean(draft));
  assert.deepEqual(clean(draft), received);
  assert.equal(hasUnsavedChanges(draft, saved), false);
  draft.days[0].exercises[0].sets = 4;
  assert.equal(hasUnsavedChanges(draft, saved), true);
  draft.days[0].exercises[0].sets = 3;
  assert.equal(hasUnsavedChanges(draft, saved), false);
});

test("rest day keeps its structural flag through hydration and save", () => {
  const withRest = {
    ...received,
    days: [
      ...received.days,
      { name: "Recuperação", description: null, isRest: true, exercises: [] },
    ],
  };
  assert.deepEqual(clean(hydrate(withRest)), withRest);
});
