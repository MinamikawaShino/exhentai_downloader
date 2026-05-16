# ExHentai Gallery Downloader

> ⚠️ **本程式由 AI 編寫。**
>
> 本程式僅作者希望將 ExHentai 的漫畫原檔下載到本地進行欣賞而編寫。**批量使用前請注意 GP 點數是否足夠使用**——腳本只會下載原檔，不會下載其他解析度的封存檔。謝謝！

ExHentai / e-hentai 畫廊封存檔自動下載器，支援 CLI 和 GUI 兩種模式。

## 已知問題

- **連接瀏覽器時可能需要數分鐘至約十分鐘**。透過遠端除錯通訊協定連接 Chrome 的耗時取決於 Chrome 設定檔大小、系統效能和網路狀況，請耐心等待，不要在此期間關閉程式。
- **中文字元顯示可能存在問題**——部分漢字可能出現大小或粗細不一致的情況，影響美觀。這是當前 GUI 字型處理的限制。

## 功能特性

- **瀏覽器接管模式**：透過 Chrome 遠端除錯通訊協定接管已有瀏覽器工作階段，手動處理 CloudFlare 驗證後自動化後續操作
- **斷點續傳**：HTTP Range 請求實現下載中斷後從斷點恢復
- **自動重試**：下載失敗自動重試（最多 3 次），支援指數退避
- **本地庫去重**：SQLite 索引本地漫畫目錄，自動跳過已下載的畫廊
- **佇列持久化**：中斷退出時自動儲存進度，重啟後可恢復
- **失敗日誌**：記錄失敗 URL 和原因，支援一鍵重試失敗項
- **畫廊元資料**：儲存標題、作者、標籤、分類到 SQLite
- **ZIP 完整性校驗**：下載完成後可選 CRC 校驗
- **自動解壓**：下載完成後可選自動解壓 ZIP 到畫廊標題子目錄
- **自訂解壓目錄**：可選擇解壓目錄（留空則為下載目錄）
- **解壓後刪除 ZIP**：可在成功解壓後刪除原始 ZIP 檔案
- **下載速度/ETA**：即時顯示下載速度和預計剩餘時間
- **桌面通知**：任務完成時桌面通知
- **多語言**：English, 简体中文, 繁體中文, 日本語, Русский
- **GUI 介面**：基於 CustomTkinter 的暗色主題桌面圖形介面

## 技術棧

| 類別 | 技術 |
|------|------|
| 語言 | Python 3.9+ |
| 瀏覽器自動化 | Selenium WebDriver (Chrome) |
| HTTP | requests |
| GUI | customtkinter |
| 資料庫 | SQLite3 |
| 設定 | JSON |

## 環境需求

- Python 3.9+
- Google Chrome 瀏覽器
- e-hentai / ExHentai 帳號

## 安裝

```bash
git clone <repo-url>
cd exhentai_downloader

pip install -r requirements.txt
```

## 使用方法

### GUI 模式（推薦）

```bash
python run.py
# 或
python -m src.main
# 或
python run.py --gui
```

1. 在 **設定** 標籤頁中設定：
   - **下載目錄**：ZIP 封存檔儲存位置
   - **解壓目錄**：選擇解壓目錄（留空則為下載目錄，每個畫廊解壓到以標題命名的子目錄）
   - **本地庫路徑**：新增已有漫畫目錄（用於去重），點擊重新掃描
   - **Chrome 瀏覽器**：設定 Chrome 路徑和使用者資料目錄
   - **語言**：選擇介面語言
   - **選項**：勾選 ZIP 完整性校驗、自動解壓、解壓後刪除 ZIP、桌面通知
2. 點擊 **啟動瀏覽器**，在開啟的 Chrome 中手動登入 e-hentai
3. 點擊 **連接瀏覽器**
4. 在 **首頁** 標籤頁中，貼上畫廊 URL（每行一個），點擊 **新增 URL**
5. 點擊 **開始下載**

### CLI 模式

```bash
python run.py --cli
# 帶參數：
python run.py --cli --language zh_tw --extract --extract-dir ./解壓目錄 --delete-after-extract
```

CLI 參數：

| 參數 | 說明 |
|------|------|
| `-l, --language` | 介面語言: `en`, `zh_cn`, `zh_tw`, `ja`, `ru` |
| `-d, --download-dir` | 下載目錄 |
| `--extract` | 下載後自動解壓 ZIP |
| `--extract-dir` | 解壓目錄（預設同下載目錄） |
| `--delete-after-extract` | 解壓後刪除 ZIP 檔案 |
| `--no-notify` | 關閉桌面通知 |
| `--no-integrity` | 跳過 ZIP 完整性校驗 |

## 工作流程

```
輸入畫廊 URL -> 導航頁面 -> 擷取標題 -> 去重檢查
    -> 點擊 Archive Download -> 取得下載連結 -> 斷點續傳下載 -> 完成
    -> [可選：完整性校驗、自動解壓、刪除ZIP、儲存元資料]
```

## 注意事項

- Chrome 必須使用 `--remote-debugging-port=9222` 參數啟動（GUI 可自動啟動）
- 首次使用需在 Chrome 中手動登入 e-hentai.org 並通過 CloudFlare 驗證
- 下載的封存檔為 ZIP 格式，檔案名為畫廊原始標題
- 開啟自動解壓後，ZIP 解壓到 `解壓目錄/畫廊標題/` 子目錄中

---

[English](README.md) | [简体中文](README.zh-cn.md) | [日本語](README.ja.md) | [Русский](README.ru.md)