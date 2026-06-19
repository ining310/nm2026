# AI Smart Recycling Bin with IOTA Wallet Reward System
Updated: 2026/6/17
## 1. Project Overview

This project proposes an **AI-powered smart recycling bin** that automatically classifies waste and physically sorts it into the correct recycling bin. The system combines **Raspberry Pi, computer vision, motor control, IOTA wallet transactions, QR-code-based user interaction, and LINE chatbot integration**.

The user first uses the camera on their phone to scan a QR code on the recycling machine. After scanning the QR code, the user is directed to a LIFF page where they enter their IOTA wallet address to register a recycling session. There is no entry fee.

After registration, the Kiosk screen on the machine switches to show a "已放置，開始偵測" button. The user **places the garbage directly onto the detection platform** (there is no entry gate), then **taps the touchscreen button** to trigger the detection process.

The Raspberry Pi camera then captures the image of the garbage. **GPT-5.5 (VLM)** classifies the item into a recycling category and determines which bin it should go into.

After classification, the Raspberry Pi controls three SG90 servo motors via PWM:
1. **Turntable servo** rotates the platform to the correct bin position (OTHER=0°, METAL=45°, PAPER=135°, PLASTIC=180°).
2. **Gate servo A + Gate servo B** open together to drop the garbage into the selected bin, then close again.

After the garbage is dropped, the turntable returns to the idle position (90°). The Raspberry Pi then calls the Lambda endpoint once with the result — the cloud immediately handles the IOTA reward or error notification and pushes the result to the user via LINE chatbot. The system then resets and waits for the next user.

If the garbage can be clearly classified as recyclable into only one category, the user receives a reward through the IOTA wallet. If the item is unclear, mixed, or not recyclable, no reward is returned.

---

## 2. Project Motivation

Recycling is important, but many people do not know how to correctly classify garbage. Incorrect recycling increases the cost of manual sorting and reduces the efficiency of recycling systems.

This project aims to solve three problems:

1. **Incorrect recycling behavior**  
   Users may not know whether an item should go to plastic, metal, paper, or general waste.

2. **Lack of motivation**  
   People may not have enough incentive to recycle correctly.

3. **Manual sorting cost**  
   Public spaces, schools, malls, and offices may need human workers to correct sorting mistakes.

The proposed system uses AI and automation to classify garbage, physically sort it, and reward users for correct recyclable items.

---

## 3. Main Objectives

The system aims to:

- Allow users to start the recycling process by scanning a QR code on the machine with their phone camera.
- Automatically identify garbage category using a Raspberry Pi camera and AI model triggered by a physical button press.
- Physically sort garbage into the correct bin using a two-motor control mechanism.
- Use an IOTA wallet mechanism to send rewards for correctly recycled items.
- Provide user interaction through a LINE chatbot.
- Demonstrate the integration of AI, IoT, blockchain, QR-code interaction, and chatbot technology.
- Encourage correct recycling behavior through financial incentives.

---

## 4. System Flow

### 4.1 High-Level Flow

```text
User scans QR code on Kiosk screen using phone camera
        ↓
User is directed to LINE LIFF page
        ↓
User enters their IOTA wallet address and clicks "登記投遞"
        ↓
Session registered (Lambda writes DynamoDB status to "paid")
        ↓
Kiosk polls GET /check every 2s → detects paid session
        ↓
Kiosk shows "已放置，開始偵測" touchscreen button
        ↓
User places garbage onto detection platform, then taps button
        ↓
Raspberry Pi camera captures image
        ↓
GPT-5.5 classifies the garbage
        ↓
Raspberry Pi turntable servo rotates to target bin position
        ↓
Gate servo A + B open → garbage drops into bin → gates close
        ↓
Turntable servo returns to idle position (90°)
        ↓
Raspberry Pi calls Lambda /result endpoint once
        ↓
Lambda pushes LINE notification → sends IOTA reward → updates DB
```

---

## 5. Detailed Operation Flow

### Step 1: User Scans the Machine

The user first opens the camera on their phone and scans the QR code displayed on the recycling machine.

The QR code can direct the user to:

- the LINE chatbot
- a LIFF page
- a payment confirmation page
- a machine-specific recycling session page

Example:

```text
User scans QR code on the machine.
System opens LINE chatbot or LIFF payment page.
```

This QR code helps the system identify which recycling machine the user is interacting with.

---

### Step 2: User Registers a Recycling Session

After scanning the QR code, the user is directed to the LIFF page. The user enters their IOTA wallet address and clicks "登記投遞". There is no entry fee.

The Lambda `/pay` endpoint writes a session record to DynamoDB (status: `paid`) and notifies the user via LINE:

```text
Bot: ✅ 登記成功！請將垃圾放上偵測平台，再按下機台上的按鈕開始偵測。
     AI 判斷可回收即可獲得 3 IOTA 獎勵。
```

---

### Step 3: User Places Garbage and Taps Touchscreen

There is no entry gate. The user places the garbage **directly onto the open detection platform**.

The Kiosk screen (running `main.py` on the Raspberry Pi) displays a "已放置，開始偵測" button after detecting a registered session. The user taps this button to start detection.

```text
User places garbage on platform → User taps "已放置，開始偵測" on screen → detection starts
```

---

### Step 4: Camera Captures Garbage Image

The Raspberry Pi camera captures an image of the garbage on the platform.

The image is sent to the AI classification model.

The AI model predicts:

- garbage category
- target bin
- confidence score
- whether it is recyclable
- whether it belongs to only one category

Example output:

```json
{
  "predicted_category": "metal",
  "target_bin": "Bin A",
  "confidence": 0.92,
  "recyclable": true,
  "single_category": true
}
```

---

### Step 5: Turntable Servo Rotates to Target Bin

The turntable servo rotates the platform to align with the correct bin. The idle position is 90° (centre). Categories map to angles as follows:

| Category | Turntable Angle |
|---|---:|
| OTHER | 0° (far left) |
| METAL | 45° (left) |
| PAPER | 135° (right) |
| PLASTIC | 180° (far right) |

Example:

```text
predicted_category = "metal"  →  Category.METAL  →  turntable rotates to 45°
```

---

### Step 6: Gate Servos Open and Drop the Garbage

After the turntable reaches the correct position, gate servo A and gate servo B rotate simultaneously to open the floor, dropping the garbage into the bin below.

```text
Gate A: 110° (closed) → 20° (open)
Gate B:  40° (closed) → 130° (open)
```

The garbage falls into the selected bin. After a short wait, both gates close back to their original positions.

---

### Step 7: Turntable Returns to Idle Position

After the gates close, the turntable servo rotates back to the centre idle position.

```text
Turntable: returns to 90° (idle)
```

---

### Step 8: Raspberry Pi Calls Lambda Once

After the motors finish, the Raspberry Pi sends **one POST request** to the Lambda `/result` endpoint with the classification result.

```json
{
  "machine_id": "machine_001",
  "session_id": "abc123",
  "category": "metal",
  "target_bin": "Bin A",
  "confidence": 0.92,
  "recyclable": true,
  "single_category": true
}
```

Lambda immediately:
1. Pushes the classification result to the user via LINE Messaging API.
2. Executes the IOTA wallet transaction (reward) or skips it.
3. Pushes the explorer URL to LINE (reward case only).
4. Updates the DynamoDB session status to `done`.

There is no polling. The RPi fires once and moves on to reset.

---

## 6. IOTA Wallet and Reward Mechanism

The system uses IOTA wallet transactions to reward users for correctly recycling. There is no entry fee — only a reward.

### 6.1 Reward Rule

After AI classification, Lambda determines whether the user should receive a reward.

There are two cases.

---

### Case 1: Clear Recyclable Item

If the garbage is classified as recyclable and belongs to only one category with confidence ≥ 80%, Lambda sends 3 IOTA to the user's wallet address.

Reward condition:

```text
classification_confidence >= 0.80
AND recyclable = true
AND single_category = true
```

Example result:

```json
{
  "category": "metal",
  "target_bin": "Bin A",
  "confidence": 0.92,
  "reward_status": "rewarded",
  "amount_sent": 3.0
}
```

---

### Case 2: Unclear, Mixed, or Non-Recyclable Item

If the garbage cannot be classified clearly, is mixed, or is not recyclable, no IOTA is sent. Lambda notifies the user via LINE.

No reward condition:

```text
classification_confidence < 0.80
OR recyclable = false
OR single_category = false
```

Example result:

```json
{
  "category": "other",
  "target_bin": "Bin D",
  "confidence": 0.43,
  "reward_status": "not_rewarded",
  "amount_sent": 0
}
```

---

## 7. LINE Chatbot Function

The LINE chatbot is the main user interface after the user scans the QR code on the machine.

Users can use the chatbot to:

- receive session registration confirmation
- receive classification result
- receive reward status or error notification with explorer URL

The chatbot also connects the user session to the specific recycling machine that was scanned.

---

## 8. Example LINE Chatbot Interaction

### 8.1 Successful Recycling Case

```text
[User scans QR code → opens LIFF page → enters wallet address → clicks 登記投遞]

Bot: ✅ 登記成功！
請將垃圾放上偵測平台，再按下機台上的按鈕開始偵測。
AI 判斷可回收即可獲得 3 IOTA 獎勵。

[User places garbage and presses button]

Bot: ♻️ 分類成功！
類別：金屬罐
信心度：92%

🎉 正在發放 3 IOTA 獎勵至您的錢包，請稍候…

Bot: 🔗 https://explorer.iota.org/txblock/...?network=devnet
```

---

### 8.2 Failed Classification Case

```text
[User scans QR code → opens LIFF page → enters wallet address → clicks 登記投遞]

Bot: ✅ 登記成功！
請將垃圾放上偵測平台，再按下機台上的按鈕開始偵測。
AI 判斷可回收即可獲得 3 IOTA 獎勵。

[User places garbage and presses button]

Bot: ❌ 無法明確分類，未發送獎勵。
類別：其他　信心度：43%
```

---

## 9. Hardware Components

| Component | Purpose |
|---|---|
| Raspberry Pi 5 | Main controller for camera, AI model, and servos |
| Raspberry Pi Camera | Captures image of garbage |
| Touchscreen Display | Shows Kiosk UI (QR code, session status, result); user taps to trigger detection |
| SG90 Turntable Servo | Rotates the platform to the correct bin position (0°/45°/135°/180°) |
| SG90 Gate Servo A | Left gate — opens/closes to drop garbage |
| SG90 Gate Servo B | Right gate — opens/closes to drop garbage |
| QR Code Label | Allows users to scan the machine and start a session |
| Detection Platform | Open tray where user places garbage for detection |
| Bins | Receive different categories of garbage |
| Power Supply | Powers Raspberry Pi and servos |

---

## 10. Software Components

| Component | Purpose |
|---|---|
| AI Classification Model | Classifies garbage category from camera image |
| Raspberry Pi Control Program | Kiosk UI (tkinter), polls session state, controls camera and motors |
| AWS Lambda + API Gateway | Cloud backend for payment, result handling, and reward logic |
| IOTA Wallet Module | Handles entry payment and reward transaction |
| LINE Chatbot / LIFF | Provides user interface after QR code scanning |
| DynamoDB | Stores user sessions, machine ID, classification results, and transaction records |

---

## 11. AI Classification Design

The Raspberry Pi camera captures an image of the garbage. The image is sent directly to **GPT-5.5 (VLM)**, which classifies the garbage into one of the following categories and determines the target bin:

| predicted_category | target_bin | IOTA Reward |
|---|---|---|
| metal | Bin A → METAL (45°) | ✓ |
| plastic | Bin B → PLASTIC (180°) | ✓ |
| paper | Bin C → PAPER (135°) | ✓ |
| other | Bin D → OTHER (0°) | ✗ |

The VLM also returns `confidence`, `recyclable`, `single_category`, and `reward_eligible` fields used by Lambda to determine whether to issue an IOTA reward.

---

## 12. Motor Control Logic

The Raspberry Pi follows this control logic:

```python
START

# Kiosk background thread polls GET /check every 2s
# When status == "paid", show "已放置，開始偵測" button on screen
wait_for_touchscreen_tap()

image_path = capture_image()              # PiCamera2 captures image
vlm_result = run_vlm(image_path)         # GPT-5.5 classifies

category = CATEGORY_MAP[vlm_result["predicted_category"]]
# e.g. "metal" → Category.METAL

recycle_bin.dispose(category)
# 1. turntable rotates to category angle
# 2. gate A + B open → garbage drops → gates close
# 3. turntable returns to idle (90°)

# Fire once — Lambda handles everything from here
send_result_to_lambda(vlm_result)

# Kiosk shows result screen for 6s, then resets to QR code screen
END
```

---

## 13. Suggested Demo Version

For the final project demo, the system can be implemented as a small-scale prototype instead of a full-size recycling bin.

### Demo Setup

The demo can include:

- one QR code printed on the machine
- one small open detection platform (no gate needed)
- one touchscreen display running the Kiosk UI
- one Raspberry Pi
- one camera
- two servo motors
  - Motor 2 for rotating to the selected bin
  - Motor 3 for dumping the garbage
- three or four mini bins
- several sample garbage items
  - metal can
  - plastic bottle
  - paper cup
  - other item (e.g. food waste)
- LINE chatbot interface
- simulated or real IOTA wallet transaction

---

### Demo Scenario

A simple demo flow can be:

```text
1. User opens the phone camera and scans the QR code on the recycling machine.
2. The QR code opens the LIFF page.
3. User enters their IOTA wallet address and clicks 登記投遞.
4. Lambda registers the session. Kiosk screen detects the new session and shows "已放置，開始偵測" button.
5. User places a metal can directly onto the detection platform.
6. User taps "已放置，開始偵測" on the Kiosk touchscreen.
7. Camera captures the image.
8. GPT-5.5 classifies it as metal → Category.METAL → turntable angle 45°.
10. Turntable servo rotates to 45°.
11. Gate servo A + B open → can drops into METAL bin → gates close.
12. Turntable returns to idle (90°).
13. Raspberry Pi calls Lambda /result once.
14. Lambda sends 3 IOTA to the user's wallet address.
15. LINE chatbot displays the reward result with explorer URL.
```
