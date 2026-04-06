import path from "node:path";

import { Command } from "commander";

import { renderScaffoldApp } from "./render-app.js";

const program = new Command();

program
  .name("modlink-plugin-scaffold")
  .description("React + Ink scaffold generator for ModLink Python driver plugins")
  .option("--zh", "use Simplified Chinese labels")
  .option("--cwd <path>", "set the output working directory", process.cwd())
  .version("0.2.0");

program.parse();

const options = program.opts<{ zh?: boolean; cwd: string }>();

if (!process.stdin.isTTY || !process.stdout.isTTY) {
  console.error("modlink-plugin-scaffold requires an interactive terminal.");
  process.exit(1);
}

renderScaffoldApp({ language: options.zh ? "zh" : "en", cwd: path.resolve(options.cwd) });
