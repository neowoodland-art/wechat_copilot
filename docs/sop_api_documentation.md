<!-- /home/neogh/wechat_copilot/docs/sop_api_documentation.md -->
# SOP API 接口文档

## 概述

SOP (Standard Operating Procedure) 自动化流程管理系统提供了完整的API接口用于管理和执行SOP流程。

## 数据结构

### SOP 定义结构

```json
{
  "sopDefinition": {
    "id": "sop_001",
    "name": "新客户欢迎SOP",
    "description": "针对新添加好友的客户执行的欢迎和初步沟通流程",
    "version": "1.0.0",
    "createdBy": "admin",
    "createdAt": "2026-02-16T10:00:00Z",
    "updatedAt": "2026-02-16T10:00:00Z",
    "isActive": true,
    "triggerConditions": [
      {
        "type": "friendAdded",
        "params": {
          "timeWindow": "24h"
        }
      }
    ],
    "nodes": [
      {
        "id": "node_001",
        "type": "delay",
        "name": "等待1分钟",
        "position": { "x": 100, "y": 100 },
        "properties": {
          "duration": 60000
        },
        "next": ["node_002"]
      },
      {
        "id": "node_002",
        "type": "message",
        "name": "发送欢迎消息",
        "position": { "x": 300, "y": 100 },
        "properties": {
          "messageType": "text",
          "content": "您好，我是{{customerName}}的专属客服，很高兴认识您！",
          "delayBeforeSend": 2000,
          "randomVariations": [
            "您好，欢迎来到我们的大家庭！",
            "很高兴认识您，有什么可以帮助您的吗？"
          ]
        },
        "next": ["node_003"]
      }
    ],
    "edges": [
      {
        "id": "edge_001",
        "source": "node_001",
        "target": "node_002",
        "type": "direct"
      }
    ],
    "variables": [
      {
        "name": "customerName",
        "type": "string",
        "source": "contact.nickname"
      }
    ],
    "errorHandling": {
      "retryAttempts": 3,
      "retryDelay": 5000,
      "fallbackSop": "defaultFollowUp",
      "notificationOnFailure": true
    },
    "analytics": {
      "trackMetrics": [
        "executionTime",
        "successRate",
        "conversionRate",
        "customerEngagement"
      ],
      "reportingSchedule": "daily"
    }
  }
}
```

## API 端点

### 创建新SOP

