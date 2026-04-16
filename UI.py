import streamlit as st
from streamlit_autorefresh import st_autorefresh
import websocket
import threading
import json
import queue
from streamlit_ace import st_ace


# === Set wide layout and auto-refresh ===
st.set_page_config(layout="wide")
st_autorefresh(interval=2000, limit=10000, key="autorefresh")

# === Shared queue and connection flag ===
@st.cache_resource
def get_shared_resources():
    return queue.Queue(), threading.Event()

msg_queue, ws_open_flag = get_shared_resources()

# === Drain messages into session state ===
while not msg_queue.empty():
    msg = msg_queue.get()
    print("✅ Queue drained:", msg)

    if not st.session_state.rule_has_been_updated and msg not in st.session_state.messages:
        st.session_state.messages.append(msg)

    if st.session_state.rule_has_been_updated and msg not in st.session_state.post_update_messages:
        st.session_state.post_update_messages.append(msg)
  

# === Session state initialization ===
defaults = {
    "message_update_index": 0,
    "connected": False,
    "ws": None,
    "ws_url": "ws://localhost:8080",
    "rule": "Initial rule",
    "updated_rule": "",
    "messages": [],
    "updated_messages": [],
    "rule_has_been_updated": False,
    "post_update_messages": [],
    "show_updated_rule_preview": False,
    "sub_message": '{"type": "subscribe", "path": "AI.Reasoner.InferenceResults", "instance": "VIN123", "schema": "Vehicle"}',
    "ws_open": False
}

for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value
    # 🔐 Don't override this flag if it's already True
    elif key == "show_updated_rule_preview" and st.session_state[key]:
        continue

# === WebSocket Callbacks ===
def on_open(ws):
    print("✅ WebSocket opened")
    ws_open_flag.set()
    msg_queue.put("✅ WebSocket connected")

def on_message(ws, message):
    print("📥 Message received:", message)
    msg_queue.put(f"📥 {message}")

def on_error(ws, error):
    print(f"❌ WebSocket error: {error}")
    msg_queue.put(f"❌ WebSocket error: {error}")

def on_close(ws, code, reason):
    print("🔌 WebSocket closed")
    ws_open_flag.clear()
    msg_queue.put("🔌 WebSocket connection closed")

def start_websocket(url):
    ws = websocket.WebSocketApp(
        url,
        on_open=on_open,
        on_message=on_message,
        on_error=on_error,
        on_close=on_close,
    )
    thread = threading.Thread(target=ws.run_forever)
    thread.daemon = True
    thread.start()
    return ws

# === Update connection status from global flag ===
st.session_state.ws_open = ws_open_flag.is_set()

# === TOP ROW: Full-width container for connection & subscription ===
with st.container():
    st.markdown("### 📡 WebSocket Connection & Subscription")

    ws_col1, ws_col2 = st.columns([3, 1])
    with ws_col1:
        st.session_state.ws_url = st.text_input("🔌 WebSocket Server URL", value=st.session_state.ws_url)
    with ws_col2:
        if st.button("✅ Connect to WebSocket"):
            st.session_state.connected = True
            st.session_state.ws = start_websocket(st.session_state.ws_url)
            st.success(f"Connecting to {st.session_state.ws_url}...")

    st.session_state.sub_message = st.text_area(
        "📝 Subscription JSON Message",
        value=st.session_state.sub_message,
        height=100
    )
    if st.button("📨 Subscribe to Data Point"):
        try:
            sub_msg = json.loads(st.session_state.sub_message)
            if (
                st.session_state.ws and
                st.session_state.ws.sock and
                st.session_state.ws.sock.connected
            ):
                st.session_state.ws.send(json.dumps(sub_msg))
                st.session_state.messages.append(f"📤 Sent: {json.dumps(sub_msg)}")
            else:
                st.session_state.messages.append("❌ WebSocket not open. Please reconnect.")
        except Exception as e:
            st.session_state.messages.append(f"❌ Invalid JSON or send failed: {e}")

    st.markdown("</div>", unsafe_allow_html=True)

# === BOTTOM ROW: Two columns side-by-side ===
left_col, right_col = st.columns(2)

# === LEFT COLUMN: Current Rule + Received Messages ===
with left_col:
    st.subheader("📜 Current Datalog Rule")
    current_rule_file = st.file_uploader("📂 Upload current .dlog rule", type=["dlog"], key="current_rule")
    # 👇 Add vertical space here
    st.markdown("<div style='height: 60px;'></div>", unsafe_allow_html=True)
    if current_rule_file:
        current_rule_content = current_rule_file.read().decode("utf-8")
        st.session_state.rule = current_rule_content  # store for access elsewhere
        st.subheader("📄 Current Rule Preview")
        left_highlighted_code = st_ace(
            value=st.session_state.rule,
            language="prolog",  # closest to Datalog
            theme="monokai",
            readonly=True,
            height=500,
            key="current_rule_view"
        )


    st.subheader("📥 Received Messages")
    pretty_msgs = []
    for raw_msg in st.session_state.messages[-10:]:
        try:
            parsed = json.loads(raw_msg.replace("📥 ", ""))
            pretty = json.dumps(parsed, indent=2)
        except Exception:
            pretty = raw_msg
        pretty_msgs.append(pretty)

    st.code("\n\n---\n\n".join(pretty_msgs), language="json",height=500)
    st.markdown("</div>", unsafe_allow_html=True)


# === RIGHT COLUMN: Rule Update via File Upload ===
with right_col:
    st.subheader("🛠️ Upload & Update Rule")

    uploaded_file = st.file_uploader("📂 Upload a .dlog rule file", type=["dlog"])

    file_content = None
    if uploaded_file:
        file_content = uploaded_file.read().decode("utf-8")

    if st.button("🔄 Update Rule"):
        if file_content:
            try:
                import requests
                from requests.auth import HTTPBasicAuth

                response = requests.put(
                    "http://localhost:12110/datastores/ds-test/content?rules",
                    data=file_content.encode("utf-8"),
                    headers={"Content-Type": "application/x.datalog"},
                    #auth=HTTPBasicAuth("project-x-admin", "test")
                    auth=HTTPBasicAuth("root", "admin")
                )
                if response.status_code in (200, 201, 204):
                    st.session_state.rule_has_been_updated = True
                    st.session_state.post_update_messages.clear()
                    st.session_state.updated_rule = file_content
                    st.session_state.updated_messages.append("✅ Rule updated successfully.")
                    print("✅ Rule updated successfully.")
                    st.session_state.show_updated_rule_preview = True  # trigger for rerender
                    st.rerun()
                else:
                    st.session_state.updated_messages.append(
                        f"❌ Update failed with status {response.status_code}: {response.text}"
                    )
                    print("❌ Update failed with status {response.status_code}: {response.text}")
            except Exception as e:
                st.session_state.updated_messages.append(f"❌ Error during update: {e}")
                print("❌ Error during update: {e}")
        else:
            st.warning("⚠️ Please upload a .dlog file before updating the rule.")


    if st.session_state.get("show_updated_rule_preview", False):
        st.subheader("📋 Updated Rule")
        st_ace(
            value=st.session_state.updated_rule,
            language="prolog",
            theme="monokai",
            readonly=True,
            height=500,
            key="updated_rule"
        )

    # ✅ Extract only messages received AFTER rule update
    post_update_msgs = st.session_state.post_update_messages[-10:]


    pretty_post_msgs = []
    for raw_msg in post_update_msgs[-10:]:
        try:
            parsed = json.loads(raw_msg.replace("📥 ", ""))
            pretty = json.dumps(parsed, indent=2)
        except Exception:
            pretty = raw_msg
        pretty_post_msgs.append(pretty)

    st.subheader("📩 Messages After Rule Update")
    st.code("\n\n---\n\n".join(pretty_post_msgs), language="json", height=500)


# === Optional Reset ===
if st.button("🧹 Reset UI"):
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()
