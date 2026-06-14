# 在 Raspberry Pi 上執行 Kiosk

## 1. 第一次設定

### 安裝相依套件

```bash
pip install openai Pillow --break-system-packages
```

### 設定環境變數

複製範本並填入實際值：

```bash
cp .env.example .env
nano .env
```

`.env` 內容：

```
MACHINE_ID=machine_001
API_BASE=https://wsmw87jtx4.execute-api.ap-northeast-1.amazonaws.com/Prod
OPENAI_API_KEY=sk-...
```

---

## 2. 每次執行

### 從 Pi 桌面的 Terminal 直接開

```bash
cd ~/Desktop/edge
python main.py
```

### 從 SSH 連線執行（需要指定 display）

```bash
DISPLAY=:0 python main.py
```

> 如果出現 `cannot connect to X server`，先在 Pi 桌面的 terminal 執行一次：
> ```bash
> xhost +local:
> ```

### 開發模式（小視窗，不全螢幕）

```bash
DISPLAY=:0 python main.py --windowed
```

---

## 3. 結束程式

全螢幕模式：按 `Esc`

SSH 模式：`Ctrl+C`

---

## 4. 更新程式

```bash
cd ~/Desktop/edge
git pull
```
