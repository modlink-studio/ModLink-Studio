import { type Instance, type RenderOptions, render } from "ink";

import { ScaffoldApp, type ScaffoldAppProps } from "./app.js";

export const scaffoldRenderOptions: RenderOptions = {
  patchConsole: true,
  maxFps: 60,
  incrementalRendering: true,
};

export function renderScaffoldApp(props: ScaffoldAppProps): Instance {
  return render(<ScaffoldApp {...props} />, scaffoldRenderOptions);
}
