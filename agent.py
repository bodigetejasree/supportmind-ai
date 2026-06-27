import os
import json
import requests
from groq import Groq
from dotenv import load_dotenv
import cascadeflow

load_dotenv()

groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
HINDSIGHT_TOKEN = os.getenv("HINDSIGHT_API_TOKEN")
HINDSIGHT_BANK = os.getenv("HINDSIGHT_BANK_ID")
HINDSIGHT_BASE = "https://api.hindsight.vectorize.io/v1"
MEMORY_FILE = "customer_memory.json"

def hindsight_recall(customer_id):
    try:
        headers = {"Authorization": f"Bearer {HINDSIGHT_TOKEN}"}
        res = requests.post(
            f"{HINDSIGHT_BASE}/banks/{HINDSIGHT_BANK}/recall",
            headers=headers,
            json={"query": f"customer {customer_id} issues orders history", "top_k": 5}
        )
        if res.status_code == 200:
            memories = res.json().get("memories", [])
            if memories:
                print(f"[Hindsight] ✅ Recalled {len(memories)} memories")
                return "\n".join([m.get("content", "") for m in memories])
    except Exception as e:
        print(f"[Hindsight] recall error: {e}")
    return None

def hindsight_retain(customer_id, issue, resolution):
    try:
        headers = {"Authorization": f"Bearer {HINDSIGHT_TOKEN}"}
        requests.post(
            f"{HINDSIGHT_BASE}/banks/{HINDSIGHT_BANK}/retain",
            headers=headers,
            json={
                "content": f"Customer {customer_id} - Issue: {issue} - Resolution: {resolution[:200]}",
                "metadata": {"customer_id": customer_id}
            }
        )
        print(f"[Hindsight] ✅ Memory saved for {customer_id}")
    except Exception as e:
        print(f"[Hindsight] retain error: {e}")

def load_local_memory():
    if os.path.exists(MEMORY_FILE):
        with open(MEMORY_FILE) as f:
            return json.load(f)
    return {}

def save_local_memory(customer_id, issue, resolution):
    memory = load_local_memory()
    if customer_id not in memory:
        memory[customer_id] = []
    memory[customer_id].append(f"Issue: {issue} | Resolution: {resolution[:150]}")
    with open(MEMORY_FILE, "w") as f:
        json.dump(memory, f, indent=2)

def get_customer_context(customer_id):
    hindsight_context = hindsight_recall(customer_id)
    if hindsight_context:
        return hindsight_context
    memory = load_local_memory()
    history = memory.get(customer_id, [])
    return "\n".join(history) if history else "No previous history."

def is_complex(message):
    keywords = ["broken", "refund", "urgent", "damaged", "fraud", "cancel", "legal", "not working", "replace"]
    return any(k in message.lower() for k in keywords)

def get_model(message):
    # cascadeflow routing logic
    if is_complex(message):
        print("[cascadeflow] 🔀 Complex query → llama-3.3-70b-versatile")
        return "llama-3.3-70b-versatile"
    else:
        print("[cascadeflow] ⚡ Simple query → llama-3.1-8b-instant (faster & cheaper)")
        return "llama-3.1-8b-instant"

def support_agent(customer_id, message):
    context = get_customer_context(customer_id)
    model = get_model(message)

    system_prompt = f"""You are a helpful customer support agent for an e-commerce company.
Customer history:
{context}

Use this history for personalized responses. Reference past issues directly.
Be concise, friendly, and specific."""

    response = groq_client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": message}
        ]
    )
    reply = response.choices[0].message.content
    hindsight_retain(customer_id, message, reply)
    save_local_memory(customer_id, message, reply)
    return reply

if __name__ == "__main__":
    print("=== SupportMind AI (Hindsight + cascadeflow) ===\n")
    customer_id = input("Enter customer ID: ").strip()
    while True:
        message = input("\nCustomer: ").strip()
        if message.lower() == "quit":
            break
        print("\nAgent:", support_agent(customer_id, message))