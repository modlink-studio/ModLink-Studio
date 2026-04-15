# ModLink Studio TODO

## 0.3.0 Data Model

- [x] 明确 `recording / session / experiment` 的主边界：`recording` 是独立资产，`session` / `experiment` 是上层组织关系
- [x] 明确 `recording_id` 的生成规则（`rec_<id>`）
- [ ] 收口 `session_id` / `experiment_id` 的生成规则
- [x] 定稿 `recording.json` 最小字段集
- [ ] 定稿 `session.json` 最小字段集
- [ ] 定稿 `experiment.json` 最小字段集
- [x] 定稿 `stream.json` 最小字段集

## Recording Storage

- [x] 将 recording 存储主路径收口为 `<storage_root>/recordings/rec_<id>/`
- [x] 将 stream 存储主路径收口为 `streams/<stream_id>/`
- [x] 去掉 `signal_csv` 作为主采集格式的方案
- [x] 收口最小 per-frame 写盘模型：`frames.csv` + `frames/*.npz`
- [x] 明确 frame 文件命名规则（顺序编号）
- [x] 明确 frame 索引文件格式（`frame_index,timestamp_ns,seq,file_name`）
- [x] 保持 storage 为函数式最小写盘工具层，不引入 writer session / finalize / readback 语义

## Recording / Qt Acquisition

- [x] Qt bridge / QML / widgets 统一使用 `storage.root_dir`
- [x] `start_recording()` 收口为只接收 `recording_label`
- [x] acquisition 录制 UI 去掉 `session_name`
- [x] 输出目录预览改为 `<storage_root>/recordings`
- [x] 录制完成提示直接使用 `RecordingStopSummary`

## Recording Catalog

- [ ] 设计 recording catalog 查询模型（不要回退到 storage 读接口）
- [ ] 设计 session / experiment catalog 查询模型
- [ ] 支持通过 catalog 将 recording 直接打开用于 replay

## Replay Backend

- [ ] 定义 `RecordingReader` 边界
- [ ] 定义 `ReplayPlayer` 边界
- [ ] 复用 `StreamDescriptor + FrameEnvelope + StreamBus` 作为回放输出接口
- [ ] 支持播放 / 暂停 / 停止 / 从头播放
- [ ] 支持 1x / 2x / 4x 倍速
- [ ] 支持 marker / segment 联动
- [x] 明确第一版不做时间轴任意拖拽

## Export Backend

- [ ] 定义 `ExportService` 边界
- [ ] 定义 `ExportJob` 状态模型
- [ ] 设计内建 exporter 注册方式（不引入插件式复杂抽象）
- [ ] 支持导出 job 排队、运行、完成、失败、取消
- [ ] 将导出产物写入 `<storage_root>/exports/<recording_id>/<job_id>/`
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
