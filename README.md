# AI Smart Recycling Bin with IOTA Wallet Reward System
Updated: 2026/6/12
## 1. Project Overview

This project proposes an **AI-powered smart recycling bin** that automatically classifies waste and physically sorts it into the correct recycling bin. The system combines **Raspberry Pi, computer vision, motor control, IOTA wallet transactions, QR-code-based user interaction, and LINE chatbot integration**.

The user first uses the camera on their phone to scan a QR code on the recycling machine. After scanning the QR code, the user is directed to the LINE chatbot or payment page, where they are asked to pay a small entry fee through an IOTA wallet.

After payment is confirmed, the user **places the garbage directly onto the detection platform** (there is no entry gate). Once the garbage is placed, the user **manually presses the physical button on the machine** to trigger the detection process.

The Raspberry Pi camera then captures the image of the garbage and uses an AI model to classify which recycling bin it should be thrown into. After classification, the Raspberry Pi controls two motors:

1. **Motor 2** rotates the internal platform to the correct bin position.
2. **Motor 3** opens the dumping door to drop the garbage into the selected bin.

After the garbage is thrown into the bin, Motor 3 closes the dumping door, and Motor 2 returns the internal platform to the original starting position. The Raspberry Pi then calls the Lambda endpoint once with the result — the cloud immediately handles the IOTA reward or error notification and pushes the result to the user via LINE chatbot. The system then resets and waits for the next user.

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
Raspberry Pi controls Motor 2 to rotate to the target bin
        ↓
Raspberry Pi controls Motor 3 to dump the garbage
        ↓
Motor 3 closes the dumping door
        ↓
Motor 2 returns to the original starting position
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

### Step 6: Motor 2 Rotates to Target Bin

Motor 2 is responsible for rotating the internal platform or chute to the correct bin position.

For example, if the garbage needs to be thrown into **Bin A**, the Raspberry Pi sends a signal to Motor 2 and tells it how many degrees it should rotate.

Example bin-angle mapping:

| Target Bin | Garbage Type Example | Motor 2 Angle |
|---|---|---:|
| Bin A | Metal can | 0° |
| Bin B | Plastic bottle | 90° |
| Bin C | Paper | 180° |
| Bin D | General waste | 270° |

If the target bin is Bin A:

```text
Raspberry Pi → Motor 2: rotate to 0°
```

If the target bin is Bin B:

```text
Raspberry Pi → Motor 2: rotate to 90°
```

---

### Step 7: Motor 3 Dumps the Garbage

After Motor 2 reaches the correct position, the Raspberry Pi sends a signal to Motor 3.

Motor 3 opens the dumping door to drop the garbage into the target bin.

Example:

```text
Raspberry Pi → Motor 3: rotate 180° to open dumping door
```

The garbage then falls into the selected bin.

---

### Step 8: Motor 3 Closes the Dumping Door

After the garbage has been dropped, Motor 3 rotates in the reverse direction to close the dumping door.

Example:

```text
Raspberry Pi → Motor 3: rotate -90° to close dumping door
```

---

### Step 9: Motor 2 Returns to Starting Position

After Motor 3 closes the dumping door, Motor 2 rotates back to the original starting position.

Example:

```text
Raspberry Pi → Motor 2: return to 0°
```

---

### Step 10: Raspberry Pi Calls Lambda Once

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
| Raspberry Pi | Main controller for camera, AI model, sensors, and motors |
| Raspberry Pi Camera | Captures image of garbage |
| Physical Button | Pressed by user to trigger detection after placing garbage |
| Motor 2 | Rotates the platform or chute to the correct bin position |
| Motor 3 | Opens/closes the dumping door |
| QR Code Label | Allows users to scan the machine and start a session |
| Detection Platform | Open tray where user places garbage for detection |
| Bins | Receive different categories of garbage |
| Power Supply | Powers Raspberry Pi and motors |

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

The AI model can be implemented in two possible ways.

### 11.1 Image Classification

The model classifies the entire image into one category.

Possible categories:

- metal can
- plastic bottle
- paper
- glass
- general waste
- unknown

This is easier to implement and suitable for the first prototype.

---

### 11.2 Object Detection

The model detects and classifies objects inside the image.

This is useful if the detection area may contain multiple items.

However, for the demo version, image classification is enough.

---

## 12. Motor Control Logic

The Raspberry Pi should follow this control logic:

```python
START

wait_for_button_press()   # GPIO interrupt, no polling

image = capture_image()

classification_result = run_ai_model(image)

target_bin = classification_result["target_bin"]

if target_bin == "Bin A":
    rotate_motor_2(angle_A)
elif target_bin == "Bin B":
    rotate_motor_2(angle_B)
elif target_bin == "Bin C":
    rotate_motor_2(angle_C)
elif target_bin == "Bin D":
    rotate_motor_2(angle_D)
else:
    rotate_motor_2(manual_check_angle)

wait_until_motor_2_reaches_position()

rotate_motor_3(open_angle)

wait_for_garbage_to_fall()

rotate_motor_3(close_angle)

rotate_motor_2(starting_angle)

# Fire once — Lambda handles everything from here
send_result_to_lambda(classification_result)

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
8. AI classifies the item as Metal Can.
9. The system selects Bin A.
10. Motor 2 rotates to Bin A.
11. Motor 3 opens the dumping door.
12. The can falls into Bin A.
13. Motor 3 closes the dumping door.
14. Motor 2 returns to the original position.
15. Raspberry Pi calls Lambda /result once.
16. Lambda sends 1.1 dollars back to the user's wallet.
17. LINE chatbot displays the reward result.
```
