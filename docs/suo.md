POST /api/v1/sop/ Content-Type: application/json


plainText

**请求体:**
```json
{
  "sopDefinition": {
    // SOP定义结构
  }
}
```

**响应:**
```json
{
  "success": true,
  "data": {
    "id": "sop_001",
    "name": "新客户欢迎SOP",
    "status": "created"
  }
}
```

### 获取SOP列表

GET /api/v1/sop/?page=1&size=10


plainText

**响应:**
```json
{
  "success": true,
  "data": [
    {
      "id": "sop_001",
      "name": "新客户欢迎SOP",
      "status": "active",
      "stepsCount": 5,
      "lastExecuted": "2026-02-16T09:30:00Z",
      "successRate": 85.5
    }
  ],
  "pagination": {
    "page": 1,
    "size": 10,
    "total": 1
  }
}
```

### 获取特定SOP详情

GET /api/v1/sop/{sop_id}


plainText

**响应:**
```json
{
  "success": true,
  "data": {
    // 完整的SOP定义结构
  }
}
```

### 更新SOP

PUT /api/v1/sop/{sop_id} Content-Type: application/json


plainText

**请求体:**
```json
{
  "sopDefinition": {
    // 更新后的SOP定义结构
  }
}
```

### 删除SOP

DELETE /api/v1/sop/{sop_id}


plainText

**响应:**
```json
{
  "success": true,
  "message": "SOP删除成功"
}
```

### 执行SOP

POST /api/v1/sop/{sop_id}/execute Content-Type: application/json


plainText

**请求体:**
```json
{
  "targetCustomerId": "customer_001",
  "context": {
    "customerName": "张三",
    "customerId": "customer_001"
  }
}
```

**响应:**
```json
{
  "success": true,
  "executionId": "exec_001",
  "status": "started",
  "estimatedCompletion": "2026-02-16T10:05:00Z"
}
```

### 获取执行状态

GET /api/v1/sop/{sop_id}/execution/{execution_id}


plainText

**响应:**
```json
{
  "success": true,
  "data": {
    "executionId": "exec_001",
    "sopId": "sop_001",
    "status": "completed",
    "progress": 100,
    "startTime": "2026-02-16T10:00:00Z",
    "endTime": "2026-02-16T10:03:45Z",
    "results": [
      {
        "nodeId": "node_001",
        "status": "completed",
        "output": "等待完成"
      },
      {
        "nodeId": "node_002",
        "status": "completed",
        "output": "消息已发送"
      }
    ]
  }
}
```

## 节点类型说明

### 1. Delay (等待节点)
```json
{
  "type": "delay",
  "properties": {
    "duration": 5000 // 等待时间(毫秒)
  }
}
```

### 2. Message (消息节点)
```json
{
  "type": "message",
  "properties": {
    "messageType": "text", // text, image, emoji
    "content": "消息内容",
    "delayBeforeSend": 2000 // 发送前延迟
  }
}
```

### 3. Condition (条件节点)
```json
{
  "type": "condition",
  "properties": {
    "conditions": [
      {
        "operator": "contains", // contains, equals, startsWith, endsWith
        "field": "lastMessage.content",
        "value": ["你好", "您好"],
        "then": "target_node_id"
      }
    ]
  }
}
```

### 4. TagCustomer (客户标记节点)
```json
{
  "type": "tagCustomer",
  "properties": {
    "tagsToAdd": ["high_intent"],
    "tagsToRemove": ["new_customer"]
  }
}
```

### 5. OCRVerify (OCR验证节点)
```json
{
  "type": "ocrVerify",
  "properties": {
    "targetElement": "message_input",
    "expectedText": "输入框已激活",
    "timeout": 10000
  }
}
```

## 错误处理

所有API端点可能返回以下标准错误格式:

```json
{
  "success": false,
  "error": {
    "code": "INVALID_SOP_DEFINITION",
    "message": "SOP定义无效",
    "details": "节点ID重复"
  }
}
```

## 状态码

- 200: 请求成功
- 400: 请求参数错误
- 404: 资源不存在
- 500: 服务器内部错误
