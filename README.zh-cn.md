# ExHentai Gallery Downloader

> ⚠️ **本程序由 AI 编写。**
>
> 本程序仅作者希望将 ExHentai 的漫画原档下载到本地进行欣赏而编写。**批量使用前请注意 GP 点数是否足够使用**——脚本只会下载原档，不会下载其他分辨率的存档。谢谢！

ExHentai / e-hentai 画廊存档自动下载器，支持 CLI 和 GUI 两种模式。

[English](README.md) | [繁體中文](README.zh-tw.md) | [日本語](README.jp.md) | [Русский](README.ru.md)

## 已知问题

- **中文字符显示可能存在问题**——部分汉字可能出现大小或粗细不一致的情况，影响美观。这是当前 GUI 字体处理的限制。

## 功能特性

- **浏览器接管模式**：通过 Chrome 远程调试协议接管已有浏览器会话，手动处理 CloudFlare 验证后自动化后续操作
- **断点续传**：HTTP Range 请求实现下载中断后从断点恢复
- **自动重试**：下载失败自动重试（最多 3 次），支持指数退避
- **本地库去重**：SQLite 索引本地漫画目录，自动跳过已下载的画廊
- **队列持久化**：中断退出时自动保存进度，重启后可恢复
- **失败日志**：记录失败 URL 和原因，支持一键重试失败项
- **画廊元数据**：保存标题、作者、标签、分类到 SQLite
- **ZIP 完整性校验**：下载完成后可选 CRC 校验
- **自动解压**：下载完成后可选自动解压 ZIP 到画廊标题子目录
- **自定义解压目录**：可选择解压目标目录（留空则为下载目录）
- **解压后删除 ZIP**：可选在成功解压后删除源 ZIP 文件
- **下载速度/ETA**：实时显示下载速度和预计剩余时间
- **桌面通知**：任务完成时桌面通知
- **多语言**：English, 简体中文, 繁體中文, 日本語, Русский
- **GUI 界面**：基于 CustomTkinter 的暗色主题桌面图形界面

## 技术栈

| 类别 | 技术 |
|------|------|
| 语言 | Python 3.9+ |
| 浏览器自动化 | Selenium WebDriver (Chrome) |
| HTTP | requests |
| GUI | customtkinter |
| 数据库 | SQLite3 |
| 配置 | JSON |

## 项目结构

```
exhentai_downloader/
├── data/                       # 持久化数据
│   └── library.db              # 本地库索引 + 元数据 (SQLite)
├── downloads/                  # 默认下载目录
├── log/
│   ├── failed_downloads.txt    # 失败下载记录
│   └── pending_queue.txt      # 崩溃恢复队列
├── src/
│   ├── main.py                 # 统一入口
│   ├── cli.py                  # CLI 实现
│   ├── downloader_core.py      # 核心下载引擎
│   ├── config.py               # 配置管理
│   ├── i18n/                   # 国际化
│   │   ├── en.py               # 英文
│   │   ├── zh_cn.py            # 简体中文
│   │   ├── zh_tw.py            # 繁体中文
│   │   ├── ja.py               # 日文
│   │   └── ru.py               # 俄文
│   ├── utils/                  # 工具
│   │   ├── filename.py         # 文件名清理
│   │   ├── integrity.py        # ZIP 完整性校验与解压
│   │   ├── logging_utils.py    # 队列与失败持久化
│   │   ├── metadata_scraper.py # 画廊元数据抓取
│   │   └── notifications.py   # 桌面通知
│   ├── db/                     # 数据库层
│   │   ├── library.py          # 本地库操作
│   │   └── metadata.py         # 画廊元数据存储
│   └── ui/                     # GUI 组件
│       ├── app.py              # 主窗口
│       ├── task_tab.py         # 任务标签页
│       ├── settings_tab.py     # 设置标签页
│       └── widgets.py          # 共享控件与工具
├── run.py                        # 入口启动器
├── requirements.txt
├── pyproject.toml
└── .gitignore
```

## 环境要求

- Python 3.9+
- Google Chrome 浏览器
- e-hentai / ExHentai 账号

## 安装

```bash
git clone <repo-url>
cd exhentai_downloader

pip install -r requirements.txt
```

## 使用方法

### GUI 模式（推荐）

```bash
python run.py
# 或
python -m src.main
# 或
python run.py --gui
```

1. 在 **设置** 标签页中配置：
   - **下载目录**：ZIP 存档保存位置
   - **解压目录**：选择解压目标目录（留空则为下载目录，每个画廊解压到以标题命名的子目录）
   - **本地库路径**：添加已有漫画目录（用于去重），点击重新扫描
   - **Chrome 浏览器**：设置 Chrome 路径和用户数据目录
   - **语言**：选择界面语言
   - **选项**：勾选 ZIP 完整性校验、自动解压、解压后删除 ZIP、桌面通知
2. 点击 **启动浏览器**，在打开的 Chrome 中手动登录 e-hentai
3. 点击 **连接浏览器**
4. 在 **主页** 标签页中，粘贴画廊 URL（每行一个），点击 **添加 URL**
5. 点击 **开始下载**

### CLI 模式

```bash
python run.py --cli
# 带参数：
python run.py --cli --language zh_cn --download-dir ./downloads --extract --extract-dir ./解压目录 --delete-after-extract
```

CLI 参数：

| 参数 | 说明 |
|------|------|
| `-l, --language` | 界面语言: `en`, `zh_cn`, `zh_tw`, `ja`, `ru` |
| `-d, --download-dir` | 下载目录 |
| `--extract` | 下载后自动解压 ZIP |
| `--extract-dir` | 解压目标目录（默认同下载目录） |
| `--delete-after-extract` | 解压后删除 ZIP 文件 |
| `--no-notify` | 关闭桌面通知 |
| `--no-integrity` | 跳过 ZIP 完整性校验 |

## 工作流程

```
输入画廊 URL -> 导航页面 -> 提取标题 -> 去重检查
    -> 点击 Archive Download -> 获取下载链接 -> 断点续传下载 -> 完成
    -> [可选：完整性校验、自动解压、删除ZIP、保存元数据]
```

## 注意事项

- Chrome 必须使用 `--remote-debugging-port=9222` 参数启动（GUI 可自动启动）
- 首次使用需在 Chrome 中手动登录 e-hentai.org 并通过 CloudFlare 验证
- 下载的存档为 ZIP 格式，文件名为画廊原标题
- 开启自动解压后，ZIP 解压到 `解压目录/画廊标题/` 子目录中

---

## 去重逻辑说明
- **同文件夹忽略**：同一个子文件夹内的图片，哪怕哈希值一样也不应该删除。
- **跨文件夹对比**：只有和其他文件夹交集对比之后才能保留最新、删除旧的图像副本。
- **文件夹去重**：当两个文件夹内相同的图像比例超过设定阈值（默认 50%）时，程序会删除修改日期最早的文件夹。
- **广告图删除功能**：去重时只提取文件夹中最后的 6 张图像（按名称排序）进行对比，如果重叠率超过设定阈值（默认 50%），则删除修改日期最早的文件夹。
- **自定义阈值**：增加了一个设置项，让用户自己选择这个重叠率比例该怎么操作。
