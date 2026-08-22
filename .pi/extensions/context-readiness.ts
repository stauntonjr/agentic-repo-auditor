import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";
import { Type } from "typebox";

const OptionSchema = Type.Object({
  label: Type.String({ description: "Short answer label" }),
  description: Type.Optional(Type.String({ description: "Consequence or tradeoff" })),
});

const QuestionSchema = Type.Object({
  id: Type.String({ description: "Stable answer identifier" }),
  prompt: Type.String({ description: "One focused question about a material context gap" }),
  options: Type.Optional(Type.Array(OptionSchema, { maxItems: 4 })),
  allowCustom: Type.Optional(Type.Boolean({ description: "Allow a free-form response; defaults to true" })),
});

const QuestionnaireSchema = Type.Object({
  questions: Type.Array(QuestionSchema, {
    minItems: 1,
    maxItems: 3,
    description: "One to three questions that cannot be answered from repository evidence",
  }),
});

type Answer = {
  id: string;
  answer: string;
  source: "selected" | "custom";
};

export default function contextReadiness(pi: ExtensionAPI) {
  pi.registerCommand("harness-adapter", {
    description: "Confirm that the repository-local harness adapter is loaded",
    handler: async (_args, ctx) => {
      ctx.ui.notify(
        "Harness adapter loaded. Canonical policy remains in AGENTS.md, .agents/skills, and harness/.",
        "info",
      );
    },
  });

  pi.registerTool({
    name: "harness_questionnaire",
    label: "Harness questionnaire",
    description:
      "Ask one to three focused follow-up questions only after repository inspection reveals material gaps in intent, authority, constraints, or acceptance. Do not use for facts that can be discovered safely.",
    parameters: QuestionnaireSchema,
    executionMode: "sequential",

    async execute(_toolCallId, params, _signal, _onUpdate, ctx) {
      if (!ctx.hasUI) {
        return {
          content: [
            {
              type: "text" as const,
              text: "Structured questions require Pi TUI or RPC UI support. Ask the focused questions directly and do not infer answers.",
            },
          ],
          details: { available: false, answers: [] as Answer[] },
        };
      }

      const answers: Answer[] = [];
      for (const question of params.questions) {
        const options = question.options ?? [];
        const allowCustom = question.allowCustom !== false;
        let answer: Answer | undefined;

        if (options.length > 0) {
          const rendered = options.map((option) =>
            option.description ? `${option.label} - ${option.description}` : option.label,
          );
          const customLabel = "Other - write a response";
          const selected = await ctx.ui.select(
            question.prompt,
            allowCustom ? [...rendered, customLabel] : rendered,
          );
          if (selected === undefined) {
            return {
              content: [{ type: "text" as const, text: "User cancelled the questionnaire." }],
              details: { available: true, cancelled: true, answers },
            };
          }
          if (selected === customLabel) {
            const custom = await ctx.ui.input(question.prompt, "Type the missing information");
            if (custom?.trim()) {
              answer = { id: question.id, answer: custom.trim(), source: "custom" };
            }
          } else {
            const index = rendered.indexOf(selected);
            answer = { id: question.id, answer: options[index].label, source: "selected" };
          }
        } else {
          const custom = await ctx.ui.input(question.prompt, "Type the missing information");
          if (custom?.trim()) {
            answer = { id: question.id, answer: custom.trim(), source: "custom" };
          }
        }

        if (!answer) {
          return {
            content: [{ type: "text" as const, text: `No answer recorded for ${question.id}.` }],
            details: { available: true, cancelled: true, answers },
          };
        }
        answers.push(answer);
      }

      return {
        content: [
          {
            type: "text" as const,
            text: answers.map((answer) => `${answer.id}: ${answer.answer}`).join("\n"),
          },
        ],
        details: { available: true, cancelled: false, answers },
      };
    },
  });
}
