# DebugMate：ModuleNotFoundError 诊断知识

## 版本信息

- source_id: `python-exceptions`
- source_url: <https://docs.python.org/3/library/exceptions.html>
- locator: `ModuleNotFoundError`
- chunk_id: `python-exceptions:module-not-found-error`
- rule_version: `module-not-found-v1`
- knowledge_build_id: `4b9be0b50bd08a13f3ebbd8ec9b80673611383001999d5b88fbfb5f3252847c1`

## 症状与分类

- 异常类型：`ModuleNotFoundError`
- 错误分类：`dependency_environment`

## 诊断事实

Python 在无法定位导入目标时会引发 `ModuleNotFoundError`；应先核对包是否安装在当前解释器环境中，以及导入名称与安装包名称是否一致。

## 诊断建议

当前报错属于依赖或解释器环境问题：Python 未能在当前导入路径中找到目标模块。先确认正在运行的解释器，再核对对应包是否安装在同一环境中。

## 检查建议

- 命令：`python -m pip show PACKAGE_NAME`
- 平台：`platform_agnostic`
- 影响：只读取当前 Python 解释器环境中的包元数据，不修改环境。
- 预期结果：若包已安装，将显示名称、版本和安装位置；否则会提示未找到该包。
- 回退：无需回滚；该命令不会修改环境。

## 安全边界

导入名称不一定等于可安装分发包名称。未确认官方分发名称和来源前，不直接生成安装命令。

## 来源锚点

- 来源：Python 官方文档
- URL：<https://docs.python.org/3/library/exceptions.html>
- 定位：`ModuleNotFoundError`
