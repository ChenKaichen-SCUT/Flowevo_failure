# 上游来源与许可

本项目是 ScienceWorld 环境适配实验，不宣称复现 FlowEvo 论文中的既有成绩。

|上游|固定提交|许可与使用方式|
|---|---|---|
|DEFENSE-SEU/FlowEvo|36e81efd4d1fdbabca7366200b15808ebef157fa|Apache-2.0；安装固定源码并直接导入原类，不整体复制上游|
|allenai/ScienceWorld|e8216d6044e8e39be9fcb185e3b2dfb602584b52|Apache-2.0；从固定源码安装包及其自带 JAR；不重新分发 JAR|
|zaoshuiban/FlowEvo-failure-driven-experiments|fde8da720f09ae823cd36c4582a9413e764ab74a|根目录未发现统一许可证；仅阅读项目说明和目录，不导入历史数据、测试答案或未声明许可的实现|

上游工作区状态、许可证指纹和 remote 见 `artifacts/upstream_manifest.json`。ScienceWorld 安装生成的版本文件和 FlowEvo 打包元数据作为安装差异记录，未修改上游求解算法。旧失败实验仓库只读，不安装其 `src`，避免同名包覆盖。

环境观测及自主运行轨迹作为实验记录发布，原环境许可仍适用。未来未使用的 TEST 清单、完整供应商网页快照和私有运行目录不在公开导出白名单内。
