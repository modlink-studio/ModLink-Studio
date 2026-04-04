import React from "react";
import {render, type Instance, type RenderOptions} from "ink";

import {ScaffoldApp, type ScaffoldAppProps} from "./app.js";

export const scaffoldRenderOptions: RenderOptions = {
  patchConsole: true,
  maxFps: 60,
  incrementalRendering: true,
};

export function renderScaffoldApp(props: ScaffoldAppProps): Instance {
  return render(<ScaffoldApp {...props} />, scaffoldRenderOptions);
}
