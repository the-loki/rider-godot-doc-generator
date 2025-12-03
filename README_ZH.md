> **AI 生成声明**：本仓库及其所有内容，包括文档和代码，均由人工智能生成。

[![Build GDScript sdk and Release](https://github.com/your-username/rider-godot-doc-generator/actions/workflows/python-app.yml/badge.svg)](https://github.com/your-username/rider-godot-doc-generator/actions/workflows/python-app.yml)

**中文**: 当前 | **English**: [README.md](README.md)

这个项目用于生成 jetbrains rider 的 godot 插件的指定语言版本文档。

## 项目简介

本项目通过github action 将godot的xml文档翻译为指定语言版本，并生成适用于 rider 的 godot 插件的 sdk。它使用godot官方的翻译文件（.po 文件）来翻译 xml 格式的文档，然后通过jetbrains的godot-support仓库中的php工具构建相应的文档。

## 如何使用

### 修改语言

要生成不同语言的 SDK，需要修改工作流程文件中的语言代码：

1. 编辑 [`.github/workflows/python-app.yml`](.github/workflows/python-app.yml) 文件
2. 找到第 13 行的全局环境变量设置：
   ```yaml
   env:
     GENERATE_LANGUAGE_CODE: zh_CN
   ```
3. 将 `zh_CN` 替换为你需要的语言代码
4. 保存文件后，推送到仓库将自动触发构建流程，生成对应语言的文档压缩包并创建 Release

## 如何使用生成的文档

下载生成的压缩包并解压，找到 rider 插件的 GdScript 目录，替换其中的 `extracted` 文件夹内容即可。
