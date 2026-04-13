# ModLink Studio TODO

## 0.3.0 Data Model

- [ ] 定稿 `recording / session / experiment` 三层边界
- [ ] 定稿 `recording_id` / `session_id` / `experiment_id` 的生成规则
- [ ] 定稿 `recording.json` 最小字段集
- [ ] 定稿 `session.json` 最小字段集
- [ ] 定稿 `experiment.json` 最小字段集
- [ ] 定稿 `stream.json` 最小字段集

## Storage Format

- [ ] 将 recording 存储主路径调整为 `data/recordings/rec_<id>/`
- [ ] 将 stream 存储主路径调整为 `streams/<stream_id>/`
- [ ] 去掉 `signal_csv` 作为主采集格式的方案
- [ ] 为 signal / raster / field / video 统一 chunked payload + timestamp index 存储模型
- [ ] 明确 chunk 文件命名规则
- [ ] 明确 chunk 索引文件格式
- [ ] 明确 finalize 时写 summary、运行时只追加索引的策略

## Recording Catalog

- [ ] 设计 recordings 列表查询模型
- [ ] 设计 sessions 列表查询模型
- [ ] 设计 experiments 列表查询模型
- [ ] 支持通过 catalog 将 recording 直接打开用于 replay
- [ ] 设计历史 recording 的 catalog 适配路径

## Replay Backend

- [ ] 定义 `RecordingReader` 边界
- [ ] 定义 `ReplayPlayer` 边界
- [ ] 复用 `StreamDescriptor + FrameEnvelope + StreamBus` 作为回放输出接口
- [ ] 支持播放 / 暂停 / 停止 / 从头播放
- [ ] 支持 1x / 2x / 4x 倍速
- [ ] 支持 marker / segment 联动
- [ ] 明确第一版不做时间轴任意拖拽

## Export Backend

- [ ] 定义 `ExportService` 边界
- [ ] 定义 `ExportJob` 状态模型
- [ ] 设计 exporter 注册表
- [ ] 支持导出 job 排队、运行、完成、失败、取消
- [ ] 将导出产物写入 `data/exports/<recording_id>/<job_id>/`
- [ ] 支持 `signal_csv`
- [ ] 支持 `signal_npz`
- [ ] 支持 `raster_npz`
- [ ] 支持 `field_npz`
- [ ] 支持 `video_frames_zip`
- [ ] 支持 `video_mp4`
- [ ] 支持 `raster_mp4`
- [ ] 支持 `field_mp4`
- [ ] 支持 `recording_bundle_zip`
- [ ] 预留后续 `BIDS` / `NWB` 导出扩展位

## Review UI

- [ ] 设计 Recording Review 页面
- [ ] 在回放页加入导出区域或导出侧栏
- [ ] 支持选择导出格式
- [ ] 支持导出参数配置
- [ ] 支持导出进度展示
- [ ] 支持导出结果路径展示

## Compatibility

- [ ] 设计旧 recording 的薄读取层
- [ ] 明确哪些旧格式字段做兼容映射
- [ ] 避免让旧目录结构继续进入新主流程

