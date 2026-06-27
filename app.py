from flask import Flask, request, jsonify, render_template_string
from agent import support_agent
import json, os

app = Flask(__name__)
TICKETS_FILE = "tickets.json"

def save_ticket(customer_id, issue, ticket_id):
    tickets = []
    if os.path.exists(TICKETS_FILE):
        with open(TICKETS_FILE) as f:
            tickets = json.load(f)
    tickets.append({"id": ticket_id, "customer_id": customer_id, "issue": issue, "status": "open"})
    with open(TICKETS_FILE, "w") as f:
        json.dump(tickets, f, indent=2)

def needs_ticket(reply):
    keywords = ["escalate", "investigate", "team", "24 hours", "48 hours", "specialist", "look into", "follow up", "check on", "contact", "assist", "help", "sorry", "issue", "problem", "broken", "repair", "replace", "fix"]
    return any(k in reply.lower() for k in keywords)

HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>SupportMind AI</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: Arial, sans-serif; background: #f0f2f5; }
        .header { background: #1a73e8; color: white; padding: 16px 24px; text-align: center; }
        .header h1 { font-size: 24px; }
        .header p { font-size: 13px; opacity: 0.8; margin-top: 4px; }
        .container { max-width: 800px; margin: 30px auto; padding: 0 16px; }
        .customer-bar { background: white; padding: 12px 16px; border-radius: 8px; margin-bottom: 16px; display: flex; align-items: center; gap: 12px; box-shadow: 0 1px 4px rgba(0,0,0,0.1); }
        .customer-bar input { flex: 1; border: 1px solid #ddd; padding: 8px 12px; border-radius: 6px; font-size: 14px; }
        .customer-bar button { background: #1a73e8; color: white; border: none; padding: 8px 16px; border-radius: 6px; cursor: pointer; }
        .chat-box { background: white; border-radius: 8px; box-shadow: 0 1px 4px rgba(0,0,0,0.1); overflow: hidden; }
        .messages { height: 450px; overflow-y: auto; padding: 20px; display: flex; flex-direction: column; gap: 12px; }
        .msg { max-width: 75%; padding: 10px 14px; border-radius: 12px; font-size: 14px; line-height: 1.5; }
        .msg.user { background: #1a73e8; color: white; align-self: flex-end; border-radius: 12px 12px 2px 12px; }
        .msg.agent { background: #f1f3f4; color: #333; align-self: flex-start; border-radius: 12px 12px 12px 2px; }
        .msg.system { background: #fff3cd; color: #856404; align-self: center; font-size: 12px; padding: 6px 12px; border-radius: 10px; }
        .ticket-btn { align-self: flex-start; margin-top: -4px; }
        .ticket-btn button { background: #1a73e8; color: white; border: none; padding: 8px 18px; border-radius: 20px; cursor: pointer; font-size: 13px; display: flex; align-items: center; gap: 6px; }
        .ticket-btn button:hover { background: #1557b0; }
        .ticket-success { background: #e8f5e9; color: #2e7d32; padding: 8px 14px; border-radius: 8px; font-size: 13px; align-self: flex-start; }
        .input-area { display: flex; padding: 16px; border-top: 1px solid #eee; gap: 10px; }
        .input-area input { flex: 1; border: 1px solid #ddd; padding: 10px 14px; border-radius: 24px; font-size: 14px; outline: none; }
        .input-area button { background: #1a73e8; color: white; border: none; padding: 10px 20px; border-radius: 24px; cursor: pointer; font-size: 14px; }
        .memory-badge { font-size: 11px; background: rgba(255,255,255,0.2); padding: 2px 8px; border-radius: 10px; margin-left: 8px; }
        .solution-box { background: #e8f5e9; border-left: 3px solid #2e7d32; padding: 10px 14px; border-radius: 0 8px 8px 0; font-size: 13px; color: #1b5e20; align-self: flex-start; max-width: 75%; }
    </style>
</head>
<body>
    <div class="header">
        <h1>🤖 SupportMind AI <span class="memory-badge">● Memory Active</span></h1>
        <p>Powered by persistent memory — I remember every customer's history</p>
    </div>
    <div class="container">
        <div class="customer-bar">
            <label style="font-size:14px;color:#555;">Customer ID:</label>
            <input type="text" id="customerId" value="customer_001" />
            <button onclick="switchCustomer()">Switch</button>
        </div>
        <div class="chat-box">
            <div class="messages" id="messages">
                <div class="msg system">Session started for <strong>customer_001</strong></div>
            </div>
            <div class="input-area">
                <input type="text" id="userInput" placeholder="Describe your issue..." onkeypress="if(event.key==='Enter') sendMessage()" />
                <button onclick="sendMessage()">Send</button>
            </div>
        </div>
    </div>

    <script>
        let currentCustomer = "customer_001";
        let lastMessage = "";
        let ticketCount = 0;

        function switchCustomer() {
            currentCustomer = document.getElementById("customerId").value.trim();
            addMsg("system", "Switched to customer: " + currentCustomer);
        }

        function addMsg(role, text, extra) {
            const msgs = document.getElementById("messages");
            const div = document.createElement("div");
            div.className = "msg " + role;
            div.textContent = text;
            msgs.appendChild(div);
            if (extra) msgs.appendChild(extra);
            msgs.scrollTop = msgs.scrollHeight;
        }

        function addTicketButton(message) {
            const msgs = document.getElementById("messages");
            const wrap = document.createElement("div");
            wrap.className = "ticket-btn";
            const btn = document.createElement("button");
btn.textContent = "🎫 Create Support Ticket";
btn.onclick = function() { createTicket(btn, message); };
wrap.appendChild(btn);
            msgs.appendChild(wrap);
            msgs.scrollTop = msgs.scrollHeight;
        }

        async function createTicket(btn, issue) {
            btn.disabled = true;
            btn.textContent = "Creating...";
            const res = await fetch("/ticket", {
                method: "POST",
                headers: {"Content-Type": "application/json"},
                body: JSON.stringify({customer_id: currentCustomer, issue})
            });
            const data = await res.json();
            const msgs = document.getElementById("messages");
            btn.parentElement.remove();
            const success = document.createElement("div");
            success.className = "ticket-success";
            success.textContent = "✅ Ticket #" + data.ticket_id + " created! Our team will follow up within 24 hours.";
            msgs.appendChild(success);
            msgs.scrollTop = msgs.scrollHeight;
        }

        async function sendMessage() {
            const input = document.getElementById("userInput");
            const message = input.value.trim();
            if (!message) return;
            lastMessage = message;
            input.value = "";
            addMsg("user", message);

            const thinking = document.createElement("div");
            thinking.className = "msg agent";
            thinking.textContent = "Thinking...";
            document.getElementById("messages").appendChild(thinking);

            const res = await fetch("/chat", {
                method: "POST",
                headers: {"Content-Type": "application/json"},
                body: JSON.stringify({customer_id: currentCustomer, message})
            });
            const data = await res.json();
            thinking.textContent = data.reply;

            if (data.needs_ticket) {
                addTicketButton(message);
            }
        }
    </script>
</body>
</html>
"""

@app.route("/")
def index():
    return render_template_string(HTML)

@app.route("/chat", methods=["POST"])
def chat():
    data = request.json
    reply = support_agent(data["customer_id"], data["message"])
    return jsonify({"reply": reply, "needs_ticket": needs_ticket(reply)})

@app.route("/ticket", methods=["POST"])
def create_ticket():
    data = request.json
    tickets = []
    if os.path.exists(TICKETS_FILE):
        with open(TICKETS_FILE) as f:
            tickets = json.load(f)
    ticket_id = len(tickets) + 1
    save_ticket(data["customer_id"], data["issue"], ticket_id)
    return jsonify({"ticket_id": ticket_id})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))