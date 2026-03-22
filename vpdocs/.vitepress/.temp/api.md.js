import { ssrRenderAttrs } from "vue/server-renderer";
import { useSSRContext } from "vue";
import { _ as _export_sfc } from "./plugin-vue_export-helper.1tPrXgE0.js";
const __pageData = JSON.parse('{"title":"API 快速索引","description":"","frontmatter":{},"headers":[],"relativePath":"api.md","filePath":"api.md","lastUpdated":null}');
const _sfc_main = { name: "api.md" };
function _sfc_ssrRender(_ctx, _push, _parent, _attrs, $props, $setup, $data, $options) {
  _push(`<div${ssrRenderAttrs(_attrs)}><h1 id="api-快速索引" tabindex="-1">API 快速索引 <a class="header-anchor" href="#api-快速索引" aria-label="Permalink to &quot;API 快速索引&quot;">​</a></h1><p>这个页面不是完整教程，而是一个快速入口页。</p><p>如果你已经知道自己要找什么类型或模块，可以直接从这里跳过去。</p><h2 id="完整-api-参考" tabindex="-1">完整 API 参考 <a class="header-anchor" href="#完整-api-参考" aria-label="Permalink to &quot;完整 API 参考&quot;">​</a></h2><p>如果你想看从源码 docstring 自动生成的 API 文档，直接跳到 pdoc：</p><ul><li><a href="./pdoc/index.html">打开 pdoc 总览</a></li></ul><p>如果你想直接看某个包：</p><ul><li><a href="./pdoc/modlink_sdk.html">modlink_sdk</a></li><li><a href="./pdoc/modlink_core.html">modlink_core</a></li><li><a href="./pdoc/modlink_ui.html">modlink_ui</a></li><li><a href="./pdoc/modlink_studio.html">modlink_studio</a></li></ul><p>如果这些链接 404，先重新构建文档站和 pdoc 产物。</p><h2 id="sdk-里最常看的对象" tabindex="-1">SDK 里最常看的对象 <a class="header-anchor" href="#sdk-里最常看的对象" aria-label="Permalink to &quot;SDK 里最常看的对象&quot;">​</a></h2><h3 id="driver" tabindex="-1"><code>Driver</code> <a class="header-anchor" href="#driver" aria-label="Permalink to &quot;\`Driver\`&quot;">​</a></h3><p>最通用的 driver 基类。</p><p>适合：</p><ul><li>callback 型设备</li><li>不适合写成固定 <code>loop()</code> 的设备</li><li>比较特殊的接入逻辑</li></ul><h3 id="loopdriver" tabindex="-1"><code>LoopDriver</code> <a class="header-anchor" href="#loopdriver" aria-label="Permalink to &quot;\`LoopDriver\`&quot;">​</a></h3><p>面向常见轮询型设备的 helper。</p><p>适合：</p><ul><li>串口轮询</li><li>BrainFlow 风格设备</li><li>一次短循环就能表达的采集逻辑</li></ul><h3 id="searchresult" tabindex="-1"><code>SearchResult</code> <a class="header-anchor" href="#searchresult" aria-label="Permalink to &quot;\`SearchResult\`&quot;">​</a></h3><p><code>search()</code> 返回的候选对象。</p><p>对 host 来说：</p><ul><li><code>title</code> / <code>subtitle</code> 用于展示</li><li><code>extra</code> 原样回传给 <code>connect_device()</code></li></ul><h3 id="streamdescriptor" tabindex="-1"><code>StreamDescriptor</code> <a class="header-anchor" href="#streamdescriptor" aria-label="Permalink to &quot;\`StreamDescriptor\`&quot;">​</a></h3><p>一个 stream 的静态说明。</p><p>最常回答的问题是：</p><ul><li>这个 stream 叫什么</li><li>这是什么模态</li><li>这个 payload 应该怎么解释</li><li><code>chunk_size</code> 和通道名是什么</li></ul><h3 id="frameenvelope" tabindex="-1"><code>FrameEnvelope</code> <a class="header-anchor" href="#frameenvelope" aria-label="Permalink to &quot;\`FrameEnvelope\`&quot;">​</a></h3><p>driver 实时发出的数据块。</p><p>最常回答的问题是：</p><ul><li>属于哪个 <code>stream_id</code></li><li>数据时间戳是什么</li><li>数据 shape 应该怎么解释</li></ul><h2 id="如果你还不确定先看哪页" tabindex="-1">如果你还不确定先看哪页 <a class="header-anchor" href="#如果你还不确定先看哪页" aria-label="Permalink to &quot;如果你还不确定先看哪页&quot;">​</a></h2><ul><li>想接设备：看 <a href="/ModLink-Studio/sdk">SDK</a></li><li>想理解运行时：看 <a href="/ModLink-Studio/core">Core</a></li><li>想做页面展示：看 <a href="/ModLink-Studio/ui">UI</a></li><li>想知道应用入口怎么挂插件：看 <a href="/ModLink-Studio/app">App</a></li></ul></div>`);
}
const _sfc_setup = _sfc_main.setup;
_sfc_main.setup = (props, ctx) => {
  const ssrContext = useSSRContext();
  (ssrContext.modules || (ssrContext.modules = /* @__PURE__ */ new Set())).add("api.md");
  return _sfc_setup ? _sfc_setup(props, ctx) : void 0;
};
const api = /* @__PURE__ */ _export_sfc(_sfc_main, [["ssrRender", _sfc_ssrRender]]);
export {
  __pageData,
  api as default
};
