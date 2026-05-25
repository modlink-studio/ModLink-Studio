# Project Working Agreement

This repository is a product codebase for ModLink Studio, not a general-purpose framework playground.

It contains app code, a headless core, an SDK, Qt bridges, and plugins, but that does not mean every layer should be designed as a reusable framework. Shared boundaries should stay minimal and should grow only from real repeated use.

## Core Principles

- Prefer short, direct code over abstract, extensible code.
- Do not add compatibility layers, migration shims, adapter layers, registries, plugin-style indirection, or framework-style extension points unless explicitly requested.
- Do not design for hypothetical future frontends, runtimes, or driver models beyond the current concrete need.
- Accept small amounts of duplication if that keeps code flatter and easier to read.
- Keep the number of files, layers, and jumps low.
- Prefer composition over inheritance when one class starts accumulating unrelated responsibilities.

## Mainline-Scripted, Implementation-Modular Code Style

- Write code in a mainline-scripted and implementation-modular style.
- Keep the structure simple, but do not minimize file count or dependency count at the expense of clarity.
- Optimize for one clear, dominant workflow. A reader should be able to follow the primary execution path from top to bottom without being forced through unnecessary abstractions.
- Make the main path feel like a clean script while organizing the implementation like a small, well-structured engineering codebase.
- The primary workflow may be somewhat longer when that keeps the real execution path visible.
- Do not shorten the main path by hiding important steps inside broad orchestration objects, generic pipelines, vague helpers, registries, or mode runners.
- For a small number of important mutually exclusive workflows, spell the branches out directly when that makes the code easier to read.
- Repetition between mutually exclusive mainline branches is acceptable if the branches are not run together and keeping them separate preserves the clarity of each main path.
- For many branches, commands, handlers, or tool calls, direct expansion can make the main path less clear. In those cases, move the dispatch responsibility into a focused function or module.
- Choose whether to spell out branches or extract dispatch based on the concrete workflow; do not apply a fixed branch-count threshold.
- A dispatch layer should be concrete and easy to follow, not a framework-style registry or hidden plugin system unless explicitly requested.
- Use modules for organization, not for over-engineering. Prefer clear files with clear responsibilities such as `config.py`, `data.py`, `model.py`, `train.py`, and `evaluate.py` when those names match the actual feature area.
- A file should own at least one clear feature or responsibility. Do not split one atomic feature across multiple files just to make files smaller.
- Files under roughly 200 lines usually do not need splitting unless responsibilities are already mixed; files over roughly 200 lines should be reviewed for feature-based separation.
- Avoid dumping unrelated helpers into vague files such as `utils.py`. Every module, class, and function should have a responsibility that can be described in one short sentence.
- Use one centralized config object as the source of truth for project settings when a workflow needs shared configuration.
- Load config once, then derive train, eval, test, model, data, UI, runtime, or service settings from that same config instance.
- Prefer clean config access such as `config.train.batch_size` or `config.model.name` over scattered dictionaries, globals, or repeated parsing.
- Keep config loading as the place where important configuration problems surface early.
- Validate critical fields, modes, paths, and values that affect startup or core workflows.
- Do not overbuild exhaustive schemas for every small option when the schema becomes harder to understand than the configuration itself.
- Keep function and class interfaces explicit. Even when values come from config, the function signature should make its real dependencies understandable.
- Avoid overly broad interfaces, many optional modes, auto-detection behavior, generic `**kwargs`, or multiple alternative calling conventions.
- Mature, stable libraries are welcome when they make the main project code cleaner and more intuitive. Do not avoid a dependency just to reduce the dependency list.
- Avoid early-stage, unstable, or rapidly changing libraries unless explicitly requested.
- For this project, be cautious about adding dependencies with strong copyleft or otherwise restrictive license obligations.
- Pythonic magic is acceptable when it matches developer intuition. Decorators, dataclasses, context managers, and similar language features are welcome if they make the main path cleaner.
- Avoid hidden global registration, import-time side effects, surprising implicit behavior, or framework magic that makes execution hard to predict.
- Do not introduce base classes, factories, registries, plugin systems, strategy patterns, or deep inheritance trees for hypothetical future needs.
- Abstraction must serve the main workflow, not an imagined future extension.
- Do not abstract merely to eliminate repetition. If two branches repeat some code but keeping them separate makes the main workflow clearer, keep the repetition.
- It is better to leave some complexity in focused tools or helper modules than to blur the main path.
- Tools and helper modules still need their own clear mainline. They are not dumping grounds for complexity.
- Functions and classes are both acceptable. Use whichever makes the boundary clearer.
- Classes should carry meaningful state or clarify the workflow; otherwise prefer functions.
- Avoid very long functions, very long classes, and objects with unclear responsibilities.
- Use type annotations on the main path and important boundaries. Core functions, public interfaces, config loaders, model builders, trainers, evaluators, and service boundaries should have clear types.
- Internal helper code may use lighter typing when stronger typing does not improve clarity.
- Prefer fail-fast behavior. If required config, files, or assumptions are missing, raise clear errors early.
- Do not silently fallback to defaults, support many input shapes, or normalize invalid cases unless explicitly requested.
- Keep comments brief and restrained. Comment on non-obvious design decisions, not on what the code mechanically does.
- Avoid collapsing an understandable main workflow into a generic `Pipeline.run()`.

## Semantic Boundaries

- Each class should have one clear semantic boundary and should only do work that belongs to that boundary.
- Do not let one class simultaneously own thread lifecycle, domain state, scheduling, event translation, and UI compatibility unless that combination is truly the single coherent job of the class.
- If a class is hard to describe in one sentence, its boundary is probably unclear.
- Each function should also have one clear semantic responsibility.
- A function may be moderately long if all of its logic serves one coherent purpose.
- Do not split cohesive logic into many tiny helper functions just to reduce line count.
- Avoid very short tool/helper functions that only forward, rename, lightly repackage, or partially delegate another nearby call.
- If a helper does not remove real complexity, it should usually not exist.

## Layer Boundaries

- Upper layers should provide only the most basic, most general context needed by lower layers.
- Do not let upper layers pre-design control surfaces for lower layers just because a specific implementation currently wants them.
- Keep host-specific behavior out of the SDK.
- Keep Qt-specific behavior out of the headless core.
- Keep bridge code focused on adaptation, not on adding new backend semantics.
- Keep process details local; return stable results upward, but do not promote lower-layer internal workflow into shared interfaces.
- If a need is not already clearly common across multiple concrete uses, keep it local.

## SDK And Core

- The SDK should expose the smallest stable contract needed by real drivers.
- Do not expand shared driver interfaces just because one convenience subclass wants more control.
- Convenience types such as `LoopDriver` should remain helpers layered on top of the core driver contract; they should not force the core runtime to take on unrelated policy unless that policy is truly part of the shared runtime model.
- The core should favor explicit state, explicit ownership, and simple data flow over clever orchestration.
- Shared backend abstractions should exist only when they clearly reduce repeated complexity across real core components.

## State, Events, And Data Flow

- Keep state representations small and concrete.
- Use one clear representation for one job; do not multiply side channels unless there is a real need.
- Keep high-frequency data paths and low-frequency control/state paths separate when that improves clarity.
- Prefer stable snapshots for pull-style state and small concrete events for push-style changes.
- Do not add event types or wrapper objects whose only job is to mirror nearby state without adding clarity.

## Abstraction Threshold

- Do not add a helper, wrapper, or intermediate type unless it clearly removes real complexity.
- Avoid thin wrappers such as one-step conversion layers, forwarding helpers, pass-through facades, or configuration-merging layers.
- Avoid creating objects whose only purpose is to move data from one nearby function to another.
- Common code should grow out of real repeated use, not anticipated reuse.
- When unsure between abstraction and duplication, default to duplication unless the abstraction is clearly simpler.

## Naming

- Names should follow the most concrete view available.
- Use domain names that match the actual responsibility of the code, not a more grandiose or more generic interpretation.
- Do not upgrade a simple queue, state holder, or worker into a broader-sounding name unless it truly owns that broader responsibility.

## Qt Widgets UI Structure

- Treat `packages/modlink_ui/` as the concrete desktop frontend for ModLink Studio, not as a reusable UI framework.
- When the Qt UI grows, prefer organizing by product feature such as `devices`, `live`, `replay`, and `settings`, not by broad buckets such as `pages`, `widgets`, and `dialogs`.
- Keep the desktop shell thin. Window chrome, navigation, and global actions belong near the shell; feature-specific state and controls belong inside the owning feature.
- Let each feature keep its own local page, dialogs, panels, and view models when they are not reused elsewhere.
- Move code into `shared` only after the same UI behavior or component is repeated across real features; do not create shared UI layers in advance.
- Keep `bridge` focused on adapting `modlink_core` state, events, and frame streams into Qt-friendly signals and snapshots. Do not let it grow into a second application service layer.
- For tables, trees, recording lists, driver lists, and other data-heavy views, prefer Qt model/view patterns over item-based widget state when the UI needs refresh, filtering, sorting, or shared state.
- When refactoring the UI, move toward `shell + features + shared + bridge`, and avoid introducing plugin-style UI extension points unless explicitly requested.

## Collaboration Rules For Codex

- Before making large edits, first align on structure if the change introduces new modules, new abstractions, or cross-layer shared code.
- When multiple designs are possible, prefer the one with fewer layers and fewer moving pieces.
- Do not preserve old APIs unless the user explicitly asks for compatibility.
- If the current code violates these rules, prefer simplifying it instead of extending the existing pattern.
- Do not introduce framework-style extensibility in the name of future growth.
- If a class or function boundary is unclear, simplify the boundary before adding new behavior.
- When implementing roadmap-related work, always update `ROADMAP.md` to reflect the current status of that item.
- After completing a planned feature, milestone, or scope change, mark it clearly in `ROADMAP.md` as planned, in progress, completed, deferred, or otherwise explicitly status-labeled.
- If implementation changes the intended version boundary or priority of a roadmap item, update `ROADMAP.md` in the same workstream instead of leaving the roadmap stale.
- In this repository, do not rely on sandboxed `pytest` execution for final verification. Request elevated execution before running `pytest`, because the sandboxed environment does not reliably provide the temp/cache filesystem access needed by the current test suite.
