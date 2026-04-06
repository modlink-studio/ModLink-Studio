# 服务端 API 手册

这份手册描述的是 `apps/modlink_server` 当前已经实现的 Web wire contract。

`modlink_server` 在 `0.2.0` 中的角色不是“已经完成的 Web UI”，而是服务化 host 边界：它把 backend 以 `HTTP + SSE + WebSocket` 的形式暴露出来，为后续 HTML / Web UI 提前固定协议。

目标读者是当前仓库里的前端和全栈开发者。默认前提是：

- 服务只运行在本机开发环境
- 默认地址是 `127.0.0.1:8000`
- 当前没有认证
- CORS 只允许 `localhost` / `127.0.0.1` 任意端口

当前服务端接口分成 3 条线：

- `HTTP`：命令与 snapshot
- `SSE`：低频事件
- `WebSocket`：高频 frame

如果只需要一个最短结论，可以先记住这条接入顺序：

1. `GET /health`
2. 拉 `drivers`、`acquisition`、`settings`、`streams/descriptors`
3. 建立 `GET /events`
4. 建立 `WS /frames`
5. 发命令后按需重新拉相关 snapshot
6. 收到 `resync_required` 后，全量重拉并重连 SSE

## 错误约定

当前 HTTP 错误响应统一是：

```json
{
  "error": {
    "type": "RuntimeError",
    "message": "recording is not active"
  }
}
```

状态码映射固定为：

- `400`：`ValueError`
- `404`：显式 `HTTPException`
- `409`：`RuntimeError`
- `504`：`TimeoutError`
- `500`：其他未处理异常

这意味着：

- 命令接口返回 `200` 时，后端命令已经执行完成，而不是“只是成功入队”
- `409` 一般表示当前状态不允许该操作
- `504` 表示底层等待超时

## Snapshot 形状

### `DriverSnapshot`

`GET /drivers` 和 `GET /drivers/{driver_id}` 返回的是 `DriverSnapshot`：

```json
{
  "driver_id": "api_demo.01",
  "display_name": "ApiDemoDriver",
  "supported_providers": ["demo"],
  "is_running": true,
  "is_connected": false,
  "is_streaming": false
}
```

### `AcquisitionSnapshot`

`GET /acquisition` 和 `GET /health` 里的 `acquisition` 字段返回的是 `AcquisitionSnapshot`：

```json
{
  "state": "idle",
  "is_started": true,
  "is_recording": false,
  "root_dir": "D:/Projects/ModLink-Studio/recordings"
}
```

## HTTP API

### Health

#### `GET /health`

用途：

- 确认服务可用
- 获取 driver 数量
- 顺手拿到 acquisition 的当前 snapshot

成功响应：

```json
{
  "ok": true,
  "driver_count": 1,
  "acquisition": {
    "state": "idle",
    "is_started": true,
    "is_recording": false,
    "root_dir": "D:/Projects/ModLink-Studio/recordings"
  }
}
```

### Drivers

#### `GET /drivers`

用途：

- 拉取所有 driver 的当前 snapshot

成功响应：

```json
[
  {
    "driver_id": "api_demo.01",
    "display_name": "ApiDemoDriver",
    "supported_providers": ["demo"],
    "is_running": true,
    "is_connected": false,
    "is_streaming": false
  }
]
```

#### `GET /drivers/{driver_id}`

用途：

- 拉取单个 driver 的当前 snapshot

常见失败：

- `404`：`driver_id` 不存在

#### `POST /drivers/{driver_id}/search`

请求体：

```json
{
  "provider": "demo"
}
```

成功响应是 `SearchResult[]`：

```json
[
  {
    "title": "API Demo Device",
    "subtitle": "demo",
    "device_id": null,
    "extra": {
      "token": "demo"
    }
  }
]
```

常见失败：

- `400`：provider 不支持
- `504`：driver search 超时

#### `POST /drivers/{driver_id}/connect`

请求体直接对应 `SearchResult` 形状：

```json
{
  "title": "API Demo Device",
  "subtitle": "demo",
  "device_id": null,
  "extra": {
    "token": "demo"
  }
}
```

成功响应：

```json
{
  "ok": true
}
```

#### `POST /drivers/{driver_id}/disconnect`

成功响应：

```json
{
  "ok": true
}
```

#### `POST /drivers/{driver_id}/start-streaming`

成功响应：

```json
{
  "ok": true
}
```

常见失败：

- `409`：driver 当前未连接，或状态不允许开始流

#### `POST /drivers/{driver_id}/stop-streaming`

成功响应：

```json
{
  "ok": true
}
```

### Streams

#### `GET /streams/descriptors`

返回当前所有已注册 stream descriptor，key 是 `stream_id`：

```json
{
  "api_demo.01.demo": {
    "device_id": "api_demo.01",
    "modality": "demo",
    "stream_id": "api_demo.01.demo",
    "payload_type": "signal",
    "nominal_sample_rate_hz": 10.0,
    "chunk_size": 4,
    "channel_names": ["demo"],
    "display_name": null,
    "metadata": {}
  }
}
```

### Acquisition

#### `GET /acquisition`

返回当前 acquisition snapshot。

#### `POST /acquisition/start-recording`

请求体：

```json
{
  "session_name": "session_001",
  "recording_label": "baseline"
}
```

成功响应：

```json
{
  "ok": true
}
```

常见失败：

- `409`：session name 非法、已经在录制、或当前状态不允许开始录制

#### `POST /acquisition/stop-recording`

成功响应：

```json
{
  "ok": true
}
```

#### `POST /acquisition/markers`

请求体：

```json
{
  "label": "blink"
}
```

成功响应：

```json
{
  "ok": true
}
```

#### `POST /acquisition/segments`

请求体：

```json
{
  "start_ns": 1000000000,
  "end_ns": 2000000000,
  "label": "trial_01"
}
```

成功响应：

```json
{
  "ok": true
}
```

### Settings

#### `GET /settings`

返回完整 nested settings snapshot。

示例：

```json
{
  "ui": {
    "preview": {
      "rate_hz": 30
    }
  },
  "acquisition": {
    "storage": {
      "root_dir": "D:/Projects/ModLink-Studio/recordings"
    }
  }
}
```

#### `PUT /settings/{key:path}`

请求体：

```json
{
  "value": 30,
  "persist": false
}
```

成功响应：

```json
{
  "ok": true
}
```

#### `DELETE /settings/{key:path}?persist=true`

示例：

```text
DELETE /settings/ui.preview.rate_hz?persist=false
```

成功响应：

```json
{
  "ok": true
}
```

## SSE 事件流

### `GET /events`

这条连接只承载低频事件。

当前首版会推 5 类消息：

- `driver_connection_lost`
- `driver_executor_failed`
- `recording_failed`
- `setting_changed`
- `resync_required`

其中前 4 类是 backend 业务/运行时事件，`resync_required` 是 transport 控制事件。

### `driver_connection_lost`

```text
event: driver_connection_lost
data: {"driver_id":"api_demo.01","detail":{"code":"DEMO_LOST"},"kind":"driver_connection_lost"}
```

payload 字段：

- `driver_id`
- `detail`
- `kind`

### `driver_executor_failed`

```text
event: driver_executor_failed
data: {"driver_id":"api_demo.01","detail":"driver executor exited unexpectedly","kind":"driver_executor_failed"}
```

payload 字段：

- `driver_id`
- `detail`
- `kind`

### `recording_failed`

```text
event: recording_failed
data: {"session_name":"session_001","recording_id":"20260403_120000","recording_path":"D:/Projects/ModLink-Studio/recordings/session_001/20260403_120000","frame_counts_by_stream":{"api_demo.01.demo":128},"reason":"frame_stream_overflow","ts_ns":1770000000000000000,"kind":"recording_failed"}
```

payload 字段：

- `session_name`
- `recording_id`
- `recording_path`
- `frame_counts_by_stream`
- `reason`
- `ts_ns`
- `kind`

### `setting_changed`

```text
event: setting_changed
data: {"key":"ui.preview.rate_hz","value":30,"ts":1770000000.0,"kind":"setting_changed"}
```

payload 字段：

- `key`
- `value`
- `ts`
- `kind`

### `resync_required`

`resync_required` 只在 event stream 自己 overflow 时出现：

```text
event: resync_required
data: {"reason":"event_stream_overflow"}
```

前端收到后建议做这 3 件事：

1. 重新拉 `drivers`、`acquisition`、`settings`、`streams/descriptors`
2. 丢弃本地旧的低频状态缓存
3. 重新连接 `GET /events`

## WebSocket 帧流

### `WS /frames`

这条连接只承载高频 frame。

`stream_id` query 规则：

- 支持重复 query：`/frames?stream_id=a&stream_id=b`
- 不传 `stream_id` 时，表示订阅全部 stream
- 首版不支持连接建立后的动态 subscribe / unsubscribe

当前服务端为每个客户端单独打开一个 `FrameStream`，并使用 `drop_oldest` 策略。这意味着前端预览更偏“保最新”，而不是“绝不丢帧”。

### 消息 schema

当前所有 payload type 都统一走 JSON 文本消息：

```json
{
  "kind": "frame",
  "stream_id": "api_demo.01.demo",
  "device_id": "api_demo.01",
  "modality": "demo",
  "payload_type": "signal",
  "timestamp_ns": 123,
  "seq": 7,
  "dtype": "float32",
  "shape": [1, 4],
  "data_base64": "AACAPwAAAEAAAEBAAACAQA==",
  "extra": {}
}
```

字段说明：

- `kind`：当前固定为 `"frame"`
- `stream_id`
- `device_id`
- `modality`
- `payload_type`
- `timestamp_ns`
- `seq`
- `dtype`
- `shape`
- `data_base64`
- `extra`

编码规则固定为：

- `data_base64 = base64(frame.data.tobytes(order="C"))`
- `dtype` 和 `shape` 用来在前端还原数组

首版不支持这些能力：

- 连接建立后的动态订阅切换
- 二进制 WebSocket frame
- 压缩协议
- 分块协议

## 推荐的前端接入顺序

可以按下面这条固定流程接：

1. `GET /health`，确认服务在线
2. 拉 `GET /drivers`
3. 拉 `GET /acquisition`
4. 拉 `GET /settings`
5. 拉 `GET /streams/descriptors`
6. 建立 `GET /events`
7. 建立 `WS /frames`
8. 发送 driver / acquisition / settings 命令后，按需重拉相关 snapshot
9. 如果收到 `resync_required`，全量重拉 snapshot，并重连 SSE

这样接的好处是：

- 低频状态始终以 snapshot 为准
- SSE 只负责增量提醒，不负责承担全部状态
- WebSocket 只负责高频 frame，不混低频业务事件
