import { ssrRenderAttrs } from "vue/server-renderer";
import { useSSRContext } from "vue";
import { _ as _export_sfc } from "./plugin-vue_export-helper.1tPrXgE0.js";
const __pageData = JSON.parse('{"title":"ModLink Studio 文档总览","description":"","frontmatter":{"layout":"home","hero":{"name":"ModLink Studio","text":"面向设备接入、多模态采集与展示的文档站","tagline":"先看怎么写 driver，再看数据怎么流动，最后再看 UI 和应用如何把这些能力组合起来","actions":[{"theme":"brand","text":"先看 SDK","link":"/sdk"},{"theme":"alt","text":"看整体架构","link":"/core"}]},"features":[{"icon":"🔌","title":"先解决接入","details":"对设备开发者来说，最重要的是先决定继承 Driver 还是 LoopDriver，然后把 SearchResult、StreamDescriptor 和 FrameEnvelope 定清楚。"},{"icon":"🧠","title":"降低心智负担","details":"常见轮询设备直接用 LoopDriver，callback 型设备直接继承 Driver。先服务最常见的写法，再保留通用底座。"},{"icon":"📡","title":"统一流模型","details":"设备接入后，系统内部都只看 stream_id、payload_type、shape 和 descriptor，不让 UI 直接依赖设备协议。"},{"icon":"🧩","title":"分层明确","details":"SDK 负责接入契约，Core 负责运行时和总线，UI 负责展示，App 负责最终组装和启动。"}]},"headers":[],"relativePath":"index.md","filePath":"index.md","lastUpdated":null}');
const _sfc_main = { name: "index.md" };
function _sfc_ssrRender(_ctx, _push, _parent, _attrs, $props, $setup, $data, $options) {
  _push(`<div${ssrRenderAttrs(_attrs)}><h1 id="modlink-studio-文档总览" tabindex="-1">ModLink Studio 文档总览 <a class="header-anchor" href="#modlink-studio-文档总览" aria-label="Permalink to &quot;ModLink Studio 文档总览&quot;">​</a></h1><p>这个站点主要服务两类人：</p><ul><li>写设备 driver 的人</li><li>在已有流模型上继续做展示、录制或应用组装的人</li></ul><p>如果你是来接设备的，推荐按下面这个顺序读：</p><ol><li><a href="/ModLink-Studio/sdk">SDK 开发者指南</a></li><li><a href="/ModLink-Studio/core">Core 模块架构</a></li><li><a href="/ModLink-Studio/api">API 快速索引</a></li></ol><p>如果你是来做展示或应用的，推荐按这个顺序读：</p><ol><li><a href="/ModLink-Studio/core">Core 模块架构</a></li><li><a href="/ModLink-Studio/ui">UI 模块架构</a></li><li><a href="/ModLink-Studio/app">App 组合根</a></li></ol><h2 id="目前这套文档重点回答什么" tabindex="-1">目前这套文档重点回答什么 <a class="header-anchor" href="#目前这套文档重点回答什么" aria-label="Permalink to &quot;目前这套文档重点回答什么&quot;">​</a></h2><ul><li>什么时候直接继承 <code>Driver</code></li><li>什么时候优先用 <code>LoopDriver</code></li><li><code>SearchResult</code>、<code>StreamDescriptor</code>、<code>FrameEnvelope</code> 各自负责什么</li><li>插件如何通过 <code>uv run --with ...</code> 挂到当前运行环境里</li><li>UI 和 Core 应该依赖哪些稳定约定，而不是依赖设备细节</li></ul><h2 id="现在最推荐的接入思路" tabindex="-1">现在最推荐的接入思路 <a class="header-anchor" href="#现在最推荐的接入思路" aria-label="Permalink to &quot;现在最推荐的接入思路&quot;">​</a></h2><p>对大多数传感器项目，建议先做这个判断：</p><ul><li>如果设备是轮询型、串口型、BrainFlow 型，优先考虑 <code>LoopDriver</code></li><li>如果设备底层是 callback 型 SDK，直接继承 <code>Driver</code></li></ul><p>然后再做这四件事：</p><ol><li>写 <code>search()</code>，返回可展示的 <code>SearchResult</code></li><li>写 <code>descriptors()</code>，定义这个设备会暴露哪些流</li><li>写连接逻辑和采集逻辑</li><li>通过 <code>sig_frame</code> 发出 <code>FrameEnvelope</code></li></ol><h2 id="你最常要找的东西" tabindex="-1">你最常要找的东西 <a class="header-anchor" href="#你最常要找的东西" aria-label="Permalink to &quot;你最常要找的东西&quot;">​</a></h2><ul><li><a href="/ModLink-Studio/sdk">SDK 页面</a>：driver 契约、LoopDriver、数据模型</li><li><a href="/ModLink-Studio/core">Core 页面</a>：driver portal、engine、stream bus、录制链路</li><li><a href="/ModLink-Studio/ui">UI 页面</a>：UI 应该依赖哪些稳定约定</li><li><a href="/ModLink-Studio/app">App 页面</a>：插件发现、应用入口、推荐启动方式</li><li><a href="/ModLink-Studio/api">API 页面</a>：pdoc 自动文档入口</li></ul></div>`);
}
const _sfc_setup = _sfc_main.setup;
_sfc_main.setup = (props, ctx) => {
  const ssrContext = useSSRContext();
  (ssrContext.modules || (ssrContext.modules = /* @__PURE__ */ new Set())).add("index.md");
  return _sfc_setup ? _sfc_setup(props, ctx) : void 0;
};
const index = /* @__PURE__ */ _export_sfc(_sfc_main, [["ssrRender", _sfc_ssrRender]]);
export {
  __pageData,
  index as default
};
