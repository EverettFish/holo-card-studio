# 多卡展厅与自动分类

`holo-card-studio` 默认交付一张独立的交互卡。当一个项目需要持续生成、浏览和分发多张卡时，建议在技能输出之外增加一个静态展厅层。技能仓库仍只包含代码和文字，人物素材、`.blend`、GLB 和渲染图继续留在用户自己的项目中。

## 一卡一目录

每张卡使用稳定且唯一的 `card-id`：

```text
web/cards/<card-id>/
├── index.html
├── app.js
├── style.css
├── card-config.json
├── card.json
├── cover.png
└── assets/
    ├── card.glb
    ├── subject.png
    ├── background.png
    ├── lineart.png
    └── text.png
```

`card-id` 建议只使用小写英文、数字和连字符。同一张卡更新时保持 ID 和 URL 不变；新卡不能覆盖旧卡目录或编号。

## 展厅元数据

每张卡新增 `card.json`，供展厅构建脚本读取：

```json
{
  "id": "tushan-date-002",
  "title": "涂山之约",
  "subtitle": "花月同心 · 传说",
  "edition": "No.002 / 002",
  "description": "月下赠花，红红执手相护。",
  "cover": "./cards/tushan-date-002/cover.png",
  "url": "./cards/tushan-date-002/",
  "createdAt": "2026-09-07",
  "characters": ["涂山红红", "自定义人物"],
  "styles": ["古风", "东方幻想"],
  "themes": ["双人", "互动", "月夜"],
  "rarity": "传说",
  "featured": true
}
```

分类直接来自元数据，不再维护重复的栏目配置：

- `characters`：人物或主体。
- `styles`：视觉语言，如古风、水墨、赛博朋克。
- `themes`：内容或场景，如双人、宠物、纪念日。
- `rarity`：统一使用普通、稀有、史诗、传说。
- `createdAt`：使用 `YYYY-MM-DD`，用于排序。
- `featured`：精选卡置顶。

构建器扫描 `web/cards/*/card.json`，验证必填字段后生成统一的 `web/cards.json`。主页读取该清单，渲染响应式瀑布流，并在浏览器内完成全文搜索和标签筛选。

## 生成后的归档流程

1. 按主流程生成素材、文字层、`card-config.json`、Blender 工程和 Three.js 页面。
2. 完成素材、GLB、WebGL、拖拽、翻面和移动端验收。
3. 确定永久 `card-id`，将网页产物复制到 `web/cards/<card-id>/`。
4. 从最终渲染图生成 `cover.png`，并填写 `card.json`。
5. 运行展厅构建器，重新生成 `cards.json`。
6. 验证首页预览、筛选、搜索和独立卡片 URL，再发布静态目录。

展厅只是分发层，不应反向修改单卡的视差、材质或 Blender 几何。glTF 仍只传递几何与材质角色；实时网页继续通过 GLSL 重建自定义全息着色。
