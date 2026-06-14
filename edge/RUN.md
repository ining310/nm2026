# 執行流程

## 目錄

- [前置：確認在最新版本](#前置確認在最新版本)
- [啟動](#啟動)
- [Demo 流程](#demo-流程)
- [注意事項](#注意事項)

---

## 前置：確認在最新版本

```bash
git pull
```

確認目前在 `main` branch：

```bash
git branch
```

---

## 啟動

```bash
cd edge
export DISPLAY=:0
python main.py
```

> RPi 螢幕亮起，顯示 QR Code。

---

## Demo 流程

1. 用手機掃描螢幕上的 QR Code
2. LINE 開啟 LIFF 頁面，選擇錢包地址
3. 按「**登記投遞**」
4. RPi 螢幕幾秒後自動切換，顯示「已放置，開始偵測」按鈕
5. 將物品放到偵測平台上
6. 按「**已放置，開始偵測**」
7. 等待偵測（相機拍照 → GPT 辨識，需等待幾下）
8. 機台開始移動，物品分流至對應回收桶
9. LINE 收到第一則訊息（分類結果）
10. IOTA 送金完成後 LINE 收到第二則訊息（Explorer 連結）
11. DB 更新完成
12. 可至 LIFF「歷史」tab 查看本次紀錄

---

## 注意事項

- 需先加 LINE 官方帳號為好友，才能收到通知
- 若某步驟失敗，`Ctrl+C` 結束後重新執行 `python main.py`
- 重跑前建議把 terminal 的錯誤訊息複製下來方便 debug
