# A2A Hybrid Pizza Agent (Streaming & Polling)

An advanced example of the Agent-to-Agent (A2A) protocol demonstrating a stateful, long-running task.

The server is hybrid: it can be accessed by clients using either real-time streaming or periodic polling to check the status of their pizza order.

---

## Prerequisites

- Python 3.10+
- Two separate terminal windows

---

## Installation

Install the required packages:

```bash
pip install "a2a-python" uvicorn fastapi httpx httpx-sse
```

---

## How to Run

### Terminal 1: Start the Server

Start the hybrid server. It will handle requests from both types of clients.

```bash
python server_hybrid.py
```

---

### Terminal 2: Choose a Client to Run

You can interact with the server using either the streaming or the polling client.

#### Option A: Streaming Client (Live Updates)

This client receives status updates instantly as they happen.

```bash
python client_streaming.py
```

#### Option B: Polling Client (Periodic Checks)

This client asks the server for the status every second.

```bash
python client_polling.py
```

---

## Usage

You can now type your order in the client terminal, for example:

```text
You: salami
```

---

## Expected Output

Both clients will produce a similar final output, but you will experience the updates differently. The streaming client receives them in real-time, while the polling client checks for them.

```text
... sending request and waiting for live updates ...

Pizzeria: Task a1b2c3d4... created with status 'submitted'.
Pizzeria: (Update) Status is now 'working': Okay, your order is being prepared. First, kneading the dough...
Pizzeria: (Update) Status is now 'working': The dough is ready and is now being rolled out.
Pizzeria: (Update) Status is now 'working': Applying tomato sauce and cheese.
Pizzeria: (Update) Status is now 'working': The fresh salami is being carefully placed on the pizza.
Pizzeria: (Update) Status is now 'working': Perfect! The pizza is now in the hot stone oven and smells delicious.
Pizzeria: (Result) Ding! 🍕 Your Salami pizza is golden-brown and ready for pickup!
Pizzeria: (Update) Status is now 'completed'

--- Next Order ---
```
