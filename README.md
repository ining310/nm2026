# AI Smart Recycling Bin with IOTA Wallet Reward System
Updated: 2026/6/12
## 1. Project Overview

This project proposes an **AI-powered smart recycling bin** that automatically classifies waste and physically sorts it into the correct recycling bin. The system combines **Raspberry Pi, computer vision, motor control, IOTA wallet transactions, QR-code-based user interaction, and LINE chatbot integration**.

The user first uses the camera on their phone to scan a QR code on the recycling machine. After scanning the QR code, the user is directed to the LINE chatbot or payment page, where they are asked to pay a small entry fee through an IOTA wallet.

After payment is confirmed, the user **places the garbage directly onto the detection platform** (there is no entry gate). Once the garbage is placed, the user **manually presses the physical button on the machine** to trigger the detection process.

The Raspberry Pi camera then captures the image of the garbage. A two-stage AI pipeline runs:
1. **Hailo AI Hat** (YOLOv8) performs real-time object detection to identify what is in the frame.
2. **GPT-4V (VLM)** classifies the item into a recycling category and determines which bin it should go into.

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
- Use an IOTA wallet mechanism to collect an entry fee and return rewards.
- Provide user interaction through a LINE chatbot.
- Demonstrate the integration of AI, IoT, blockchain, QR-code interaction, and chatbot technology.
- Encourage correct recycling behavior through financial incentives.

---

## 4. System Flow

### 4.1 High-Level Flow

```text
User scans QR code on the recycling machine using phone camera
        ↓
User is directed to LINE chatbot or LIFF payment page
        ↓
User pays 1 dollar through IOTA wallet
        ↓
Payment confirmed (Lambda updates DynamoDB status to "paid")
        ↓
User places garbage directly onto the detection platform
        ↓
User presses the physical button on the machine
        ↓
Raspberry Pi camera captures image
        ↓
AI model classifies the garbage
        ↓
Raspberry Pi turntable servo rotates to target bin position
        ↓
Gate servo A + B open → garbage drops into bin → gates close
        ↓
Turntable servo returns to idle position (90°)
        ↓
Raspberry Pi calls Lambda /result endpoint once
        ↓
Lambda immediately sends IOTA reward or error notification + LINE push
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

### Step 2: User Starts a Recycling Session

After scanning the QR code, the user enters the LINE chatbot or web-based payment interface.

Example:

```text
User: I want to recycle.
Bot: Please pay 1 dollar to start the recycling session.
```

---

### Step 3: User Pays Entry Fee

The user pays a fixed entry fee through the IOTA wallet.

Example:

```text
Entry fee: 1 dollar
```

After the payment is confirmed, the Lambda backend updates DynamoDB and notifies the user to proceed.

Example LINE message:

```text
Bot: Payment confirmed. Please place your garbage onto the detection platform,
then press the button on the machine to start detection.
```

---

### Step 4: User Places Garbage and Presses Button

There is no entry gate. The user places the garbage **directly onto the open detection platform**.

After placing the garbage, the user **manually presses the physical button** on the machine.

The button is connected to a Raspberry Pi GPIO pin configured as an interrupt. When the button is pressed, the Raspberry Pi immediately starts the detection process.

```text
User places garbage on platform → User presses button → GPIO interrupt fires → detection starts
```

---

### Step 5: Camera Captures Garbage Image

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
  "predicted_category": "metal_can",
  "target_bin": "Bin A",
  "confidence": 0.92,
  "recyclable": true,
  "single_category": true
}
```

---

### Step 6: Turntable Servo Rotates to Target Bin

The turntable servo rotates the platform to align with the correct bin. The idle position is 90° (centre). Categories map to angles as follows:

| Category | Turntable Angle |
|---|---:|
| OTHER | 0° (far left) |
| METAL | 45° (left) |
| PAPER | 135° (right) |
| PLASTIC | 180° (far right) |

Example:

```text
predicted_category = "metal_can"  →  Category.METAL  →  turntable rotates to 45°
```

---

### Step 7: Gate Servos Open and Drop the Garbage

After the turntable reaches the correct position, gate servo A and gate servo B rotate simultaneously to open the floor, dropping the garbage into the bin below.

```text
Gate A: 110° (closed) → 20° (open)
Gate B:  40° (closed) → 130° (open)
```

The garbage falls into the selected bin. After a short wait, both gates close back to their original positions.

---

### Step 8: Turntable Returns to Idle Position

After the gates close, the turntable servo rotates back to the centre idle position.

```text
Turntable: returns to 90° (idle)
```

---

### Step 9: Raspberry Pi Calls Lambda Once

After the motors finish, the Raspberry Pi sends **one POST request** to the Lambda `/result` endpoint with the classification result.

```json
{
  "machine_id": "machine_001",
  "session_id": "abc123",
  "category": "metal_can",
  "target_bin": "Bin A",
  "confidence": 0.92,
  "recyclable": true,
  "single_category": true
}
```

Lambda immediately:
1. Determines reward or no-reward based on the result.
2. Executes the IOTA wallet transaction (reward) or skips it.
3. Pushes the result to the user via LINE Messaging API.
4. Updates the DynamoDB session status to `done`.

There is no polling. The RPi fires once and moves on to reset.

---

## 6. IOTA Wallet and Reward Mechanism

The system uses IOTA wallet transactions to create a deposit-and-reward recycling mechanism.

### 6.1 Entry Fee

Before throwing garbage, each user must pay:

```text
1 dollar
```

This payment acts as an entry fee or deposit.

---

### 6.2 Reward Rule

After AI classification, Lambda determines whether the user should receive a reward.

There are two main cases.

---

### Case 1: Clear Recyclable Item

If the garbage is classified as recyclable and belongs to only one category, Lambda sends money back to the user's IOTA wallet.

Example:

```text
User pays: 1.0 dollar
User receives: 1.1 dollars
Net reward: +0.1 dollar
```

Reward condition:

```text
classification_confidence >= threshold
AND recyclable = true
AND single_category = true
```

Example result:

```json
{
  "category": "metal_can",
  "target_bin": "Bin A",
  "confidence": 0.92,
  "reward_status": "rewarded",
  "amount_returned": 1.1
}
```

---

### Case 2: Unclear, Mixed, or Non-Recyclable Item

If the garbage cannot be classified clearly, is mixed, or is not recyclable, Lambda does not send money back and notifies the user of the issue.

Example:

```text
User pays: 1.0 dollar
User receives: 0 dollar
Net result: -1.0 dollar
```

No reward condition:

```text
classification_confidence < threshold
OR recyclable = false
OR single_category = false
```

Example result:

```json
{
  "category": "unknown",
  "target_bin": "manual_check",
  "confidence": 0.43,
  "reward_status": "not_rewarded",
  "amount_returned": 0
}
```

---

## 7. LINE Chatbot Function

The LINE chatbot is the main user interface after the user scans the QR code on the machine.

Users can use the chatbot to:

- start a recycling session
- connect or identify their IOTA wallet
- pay the entry fee
- receive classification result
- receive reward status or error notification
- view wallet transaction history
- view personal recycling history

The chatbot also connects the user session to the specific recycling machine that was scanned.

---

## 8. Example LINE Chatbot Interaction

### 8.1 Successful Recycling Case

```text
User scans the QR code on the machine.

Bot: Welcome to the AI Smart Recycling Bin.
Please pay 1 dollar to start the recycling session.

User: Paid.

Bot: Payment confirmed.
Please place your garbage onto the detection platform,
then press the button on the machine.

[User places garbage and presses button]

Bot: Your item was classified as Metal Can.
Target bin: Bin A.
Confidence: 92%.
Reward status: Success.
1.1 dollars have been sent back to your wallet.
Thank you for recycling correctly.
```

---

### 8.2 Failed Classification Case

```text
User scans the QR code on the machine.

Bot: Welcome to the AI Smart Recycling Bin.
Please pay 1 dollar to start the recycling session.

User: Paid.

Bot: Payment confirmed.
Please place your garbage onto the detection platform,
then press the button on the machine.

[User places garbage and presses button]

Bot: The item could not be clearly classified.
Classification result: Unknown or mixed waste.
Reward status: No reward returned.
Please check the recycling rules before trying again.
```

---

## 9. Hardware Components

| Component | Purpose |
|---|---|
| Raspberry Pi 5 | Main controller for camera, AI model, GPIO button, and servos |
| Hailo AI Hat | Runs YOLOv8 object detection on-device in real time |
| Raspberry Pi Camera | Captures image of garbage |
| Physical Button | Pressed by user to trigger detection after placing garbage |
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
| Raspberry Pi Control Program | Controls camera, GPIO button interrupt, and two motors |
| AWS Lambda + API Gateway | Cloud backend for payment, result handling, and reward logic |
| IOTA Wallet Module | Handles entry payment and reward transaction |
| LINE Chatbot / LIFF | Provides user interface after QR code scanning |
| DynamoDB | Stores user sessions, machine ID, classification results, and transaction records |

---

## 11. AI Classification Design

The system uses a two-stage AI pipeline:

### 11.1 Stage 1 — Hailo Object Detection (YOLOv8)

The Hailo AI Hat runs YOLOv8 on-device to detect objects in the captured image. It returns the top detected object label and confidence score. This stage acts as a fast pre-filter and provides the image path for stage 2.

### 11.2 Stage 2 — GPT-4V Visual Language Model (VLM)

The captured image is sent to GPT-4V, which classifies the garbage into one of the following categories and determines the target bin:

| predicted_category | target_bin |
|---|---|
| metal_can | Bin A → METAL (45°) |
| plastic_bottle | Bin B → PLASTIC (180°) |
| paper | Bin C → PAPER (135°) |
| glass | Bin D → OTHER (0°) |
| general_waste | manual_check → OTHER (0°) |
| unknown | manual_check → OTHER (0°) |
| multiple_categories | manual_check → OTHER (0°) |

The VLM also returns `confidence`, `recyclable`, `single_category`, and `reward_eligible` fields used by Lambda to determine whether to issue an IOTA reward.

---

## 12. Motor Control Logic

The Raspberry Pi follows this control logic:

```python
START

wait_for_button_press()          # GPIO interrupt, no polling

hailo_result = detect_object_detailed()   # Stage 1: Hailo YOLOv8
vlm_result   = run_vlm(hailo_result["image_path"])  # Stage 2: GPT-4V

category = CATEGORY_MAP[vlm_result["predicted_category"]]
# e.g. "metal_can" → Category.METAL

recycle_bin.dispose(category)
# 1. turntable rotates to category angle
# 2. gate A + B open → garbage drops → gates close
# 3. turntable returns to idle (90°)

# Fire once — Lambda handles everything from here
send_result_to_lambda(vlm_result)

END
```

---

## 13. Suggested Demo Version

For the final project demo, the system can be implemented as a small-scale prototype instead of a full-size recycling bin.

### Demo Setup

The demo can include:

- one QR code printed on the machine
- one small open detection platform (no gate needed)
- one physical push button connected to Raspberry Pi GPIO
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
  - unknown object
- LINE chatbot interface
- simulated or real IOTA wallet transaction

---

### Demo Scenario

A simple demo flow can be:

```text
1. User opens the phone camera and scans the QR code on the recycling machine.
2. The QR code opens the LINE chatbot or LIFF page.
3. User pays 1 dollar.
4. The system confirms payment and sends a LINE message asking the user to place the garbage and press the button.
5. User places a metal can directly onto the detection platform.
6. User presses the physical button on the machine.
7. Camera captures the image.
8. Hailo detects an object in the frame.
9. GPT-4V classifies it as metal_can → Category.METAL → turntable angle 45°.
10. Turntable servo rotates to 45°.
11. Gate servo A + B open → can drops into METAL bin → gates close.
12. Turntable returns to idle (90°).
13. Raspberry Pi calls Lambda /result once.
14. Lambda sends 1.1 IOTA back to the user's wallet.
15. LINE chatbot displays the reward result with explorer URL.
```
