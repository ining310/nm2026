# IOTA 送獎勵流程

## 使用套件

沒有官方 IOTA Python SDK，全部用標準 HTTP + 加密套件自行實作：

```python
import requests       # 發送 JSON-RPC
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
import hashlib        # blake2b 雜湊
import base64         # 簽章編碼
```

---

## 前置：私鑰 → 地址推導

```
私鑰 (32 bytes hex，存在 AWS SSM Parameter Store)
    ↓  Ed25519PrivateKey.from_private_bytes()
公鑰 (32 bytes raw)
    ↓  blake2b( 公鑰, digest_size=32 )
地址 = "0x" + blake2b 結果
```

---

## Step 1：查詢機台錢包的 coin

```
RPC: iotax_getCoins(sender_address)
→ 回傳此地址擁有的所有 IOTA coin 物件
→ 選餘額最大的 coin（作為 gas + 轉帳來源）
```

---

## Step 2：建立未簽名交易

```
RPC: unsafe_transferIota(
    sender,          # 機台地址
    coin_object_id,  # Step 1 選出的 coin
    gas_budget,      # 0.01 IOTA（手續費上限）
    recipient,       # 使用者錢包地址
    amount           # 3_000_000_000 MIST = 3 IOTA
)
→ 回傳 tx_bytes（base64 編碼的未簽名交易）
```

---

## Step 3：本地簽章（不上鏈）

```
待簽資料 = blake2b( [0x00, 0x00, 0x00] + tx_bytes )
                     ↑ intent prefix（3 bytes）

簽章 = Ed25519.sign( 私鑰, 待簽資料 )  →  64 bytes

envelope = [0x00]      # Ed25519 flag
         + 簽章 (64B)
         + 公鑰 (32B)

signature = base64( envelope )  →  97 bytes base64 字串
```

---

## Step 4：廣播上鏈

```
RPC: iota_executeTransactionBlock(
    tx_bytes,
    [signature],
    showEffects=True,
    "WaitForLocalExecution"  # 等本地節點確認後才回傳
)
→ 回傳 { digest: "交易 hash", ... }
→ explorer_url = https://explorer.iota.org/txblock/{digest}?network=devnet
```

---

## 整體時序

```
Lambda 呼叫 send_reward()
    ↓  ~100ms
查 coins（RPC #1）
    ↓  ~200ms
建立交易（RPC #2）
    ↓  ~1ms（本地計算）
Ed25519 簽章
    ↓  10–60s（取決於 devnet 節點狀態）
廣播 + 等確認（RPC #3）
    ↓
回傳 digest + explorer_url → 推播至 LINE
```

> devnet 節點不穩定時，最後一步可能需要 60 秒以上，Lambda timeout 設為 120 秒以因應。

---

## 驗證

本地程式不做簽章驗證，直接廣播後由 **IOTA 網路的 validator 節點**負責：

- 驗證 Ed25519 簽章正確性
- 確認 sender 餘額足夠
- 交易合法後寫入帳本

---

## 私鑰安全性

私鑰以加密形式存於 **AWS SSM Parameter Store**，Lambda 啟動時透過環境變數讀取，不寫入程式碼或版本控制：

```python
hex_key = os.environ["IOTA_MACHINE_PRIVATE_KEY_HEX"]
pk_bytes = bytes.fromhex(hex_key)
```
