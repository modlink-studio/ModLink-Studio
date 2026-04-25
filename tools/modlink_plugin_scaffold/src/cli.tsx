import path from "node:path";
import process from "node:process";

import { Command } from "commander";

import {
  generateScaffoldProject,
  scaffoldJsonSchema,
  validateScaffoldInput,
} from "./lib/headless.js";
import type { Language } from "./lib/types.js";
import { renderScaffoldApp } from "./render-app.js";

const program = new Command();

async function readStdinJson(): Promise<unknown> {
  const chunks: Buffer[] = [];
  for await (const chunk of process.stdin) {
    chunks.push(Buffer.isBuffer(chunk) ? chunk : Buffer.from(chunk));
  }
  const raw = Buffer.concat(chunks).toString("utf8").trim();
  if (!raw) {
    throw new Error("Expected JSON input on stdin.");
  }
  return JSON.parse(raw);
}

function writeJson(value: object): void {
  process.stdout.write(`${JSON.stringify(value, null, 2)}\n`);
}

function languageFromOptions(options: { zh?: boolean }): Language {
  return options.zh ? "zh" : "en";
}

program
  .name("modlink-plugin-scaffold")
  .description(
    "Generate ModLink Python driver plugin projects. Use the default interactive TUI for developers, or headless generate/validate/schema commands for AI agents, CI, and scripts.",
  )
  .option("--zh", "use Simplified Chinese labels")
  .option("--cwd <path>", "set the output working directory", process.cwd())
  .version("0.2.0")
  .showHelpAfterError()
  .action((options: { zh?: boolean; cwd: string }) => {
    if (!process.stdin.isTTY || !process.stdout.isTTY) {
      console.error(
        "modlink-plugin-scaffold interactive mode requires a TTY. Use generate/validate/schema for headless AI or CI usage.",
      );
      process.exit(1);
    }

    renderScaffoldApp({
      language: languageFromOptions(options),
      cwd: path.resolve(options.cwd),
    });
  });

program
  .command("schema")
  .description("Print the JSON schema accepted by headless generate and validate commands.")
  .option("--json", "emit machine-readable JSON", true)
  .action(() => {
    writeJson({ ok: true, schema: scaffoldJsonSchema() });
  });

program
  .command("validate")
  .description("Validate a scaffold JSON spec from stdin without writing files.")
  .option("--stdin", "read scaffold JSON from stdin")
  .option("--json", "emit machine-readable JSON", true)
  .option("--zh", "use Simplified Chinese validation labels")
  .action(async (options: { stdin?: boolean; zh?: boolean }) => {
    if (!options.stdin) {
      throw new Error("validate requires --stdin.");
    }
    const input = await readStdinJson();
    const result = validateScaffoldInput(languageFromOptions(options), input);
    writeJson(result);
    if (!result.ok) {
      process.exitCode = 1;
    }
  });

program
  .command("generate")
  .description("Generate a scaffold project from JSON stdin for AI agents, CI, or scripts.")
  .requiredOption("--out <path>", "output directory that will contain the generated plugin project")
  .option("--stdin", "read scaffold JSON from stdin")
  .option("--json", "emit machine-readable JSON", true)
  .option("--zh", "use Simplified Chinese generated README labels")
  .option("--overwrite", "replace an existing generated plugin directory")
  .action(async (options: { out: string; stdin?: boolean; zh?: boolean; overwrite?: boolean }) => {
    if (!options.stdin) {
      throw new Error("generate requires --stdin.");
    }
    const input = await readStdinJson();
    const result = await generateScaffoldProject(
      languageFromOptions(options),
      input,
      path.resolve(options.out),
      options.overwrite === true,
    );
    writeJson(result);
    if (!result.ok) {
      process.exitCode = 1;
    }
  });

program.parseAsync().catch((error: unknown) => {
  const message = error instanceof Error ? error.message : String(error);
  console.error(message);
  process.exit(1);
});
