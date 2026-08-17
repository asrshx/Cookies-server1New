import streamlit as st
import requests
import threading
import time
import random
import string
from datetime import datetime

# Page configuration
st.set_page_config(
    page_title="Cookies Server Made By Sanskari Ladka",
    page_icon="☠️",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# Custom CSS
st.markdown("""
<style>
    .main {
        background-image: url('https://ibb.co/gFg8pMtj.jpeg');
        background-size: cover;
        background-repeat: no-repeat;
        background-attachment: fixed;
    }
    .stApp {
        background: rgba(0, 0, 0, 0.8);
    }
    .title-text {
        text-align: center;
        color: Black;
        font-size: 2.5em;
        font-weight: bold;
        text-shadow: 2px 2px 4px #000000;
        animation: glow 1s ease-in-out infinite alternate;
    }
    @keyframes glow {
        from { text-shadow: 0 0 10px #fff, 0 0 20px #fff, 0 0 30px #e60073; }
        to { text-shadow: 0 0 20px #fff, 0 0 30px #ff4da6, 0 0 40px #ff4da6; }
    }
    .success-box {
        background: rgba(0, 255, 0, 0.2);
        border: 2px solid #00ff00;
        border-radius: 10px;
        padding: 20px;
        margin: 10px 0;
        color: #00ff00;
        text-align: center;
    }
    .error-box {
        background: rgba(255, 0, 0, 0.2);
        border: 2px solid #ff0000;
        border-radius: 10px;
        padding: 20px;
        margin: 10px 0;
        color: #ff9900;
        text-align: center;
    }
    .info-box {
        background: rgba(0, 0, 255, 0.2);
        border: 2px solid #0000ff;
        border-radius: 10px;
        padding: 20px;
        margin: 10px 0;
        color: #00ffff;
        text-align: center;
    }
    .stTextInput input, .stTextArea textarea, .stNumberInput input {
        background: rgba(255, 255, 255, 0.1) !important;
        color: white !important;
        border: 2px solid white !important;
        border-radius: 10px !important;
    }
    .stSelectbox div[data-baseweb="select"] {
        background: rgba(255, 255, 255, 0.1) !important;
        color: white !important;
        border: 2px solid wihite !important;
        border-radius: 10px !important;
    }
    .stFileUploader section {
        background: rgba(255, 255, 255, 0.1) !important;
        border: 2px dashed black !important;
        border-radius: 10px !important;
    }
</style>
""", unsafe_allow_html=True)

# Headers for requests
headers = {
    'Connection': 'keep-alive',
    'Cache-Control': 'max-age=0',
    'Upgrade-Insecure-Requests': '1',
    'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/56.0.2924.76 Safari/537.36',
    'user-agent': 'Mozilla/5.0 (Linux; Android 11; TECNO CE7j) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/101.0.4951.40 Mobile Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
    'Accept-Encoding': 'gzip, deflate',
    'Accept-Language': 'en-US,en;q=0.9,fr;q=0.8',
    'referer': 'www.google.com'
}

# Initialize session state
if 'tasks' not in st.session_state:
    st.session_state.tasks = {}
if 'stop_events' not in st.session_state:
    st.session_state.stop_events = {}
if 'active_threads' not in st.session_state:
    st.session_state.active_threads = {}
if 'message_log' not in st.session_state:
    st.session_state.message_log = []

def send_messages(cookies_list, thread_id, mn, time_interval, messages, task_id):
    """Function to send messages using Facebook cookies"""
    stop_event = st.session_state.stop_events[task_id]
    st.session_state.tasks[task_id] = {"status": "Running", "start_time": datetime.now()}
    
    message_count = 0
    while not stop_event.is_set():
        for message1 in messages:
            if stop_event.is_set():
                break
            for cookie in cookies_list:
                if stop_event.is_set():
                    break
                try:
                    api_url = f'https://graph.facebook.com/v15.0/t_{thread_id}/'
                    message = str(mn) + ' ' + message1
                    
                    # Create session with cookies
                    session = requests.Session()
                    
                    # Parse cookie string into dictionary
                    cookie_dict = {}
                    for c in cookie.strip().split(';'):
                        if '=' in c:
                            key, value = c.strip().split('=', 1)
                            cookie_dict[key] = value
                    
                    # Add cookies to session
                    session.cookies.update(cookie_dict)
                    session.headers.update(headers)
                    
                    parameters = {'message': message}
                    response = session.post(api_url, data=parameters)
                    
                    if response.status_code == 200:
                        log_message = f"✅ Message Sent: {message}"
                        st.session_state.message_log.append(log_message)
                        message_count += 1
                    else:
                        log_message = f"❌ Failed (Status {response.status_code}): {message}"
                        st.session_state.message_log.append(log_message)
                    
                    # Keep only last 50 messages in log
                    if len(st.session_state.message_log) > 50:
                        st.session_state.message_log.pop(0)
                        
                    time.sleep(time_interval)
                except Exception as e:
                    log_message = f"⚠️ Error: {str(e)}"
                    st.session_state.message_log.append(log_message)
                    time.sleep(2)
    
    st.session_state.tasks[task_id]["status"] = "Stopped"
    st.session_state.tasks[task_id]["end_time"] = datetime.now()
    st.session_state.tasks[task_id]["total_messages"] = message_count

def start_task(cookies_list, thread_id, mn, time_interval, messages):
    """Start a new message sending task"""
    task_id = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
    
    # Create stop event for this task
    st.session_state.stop_events[task_id] = threading.Event()
    
    # Start thread
    thread = threading.Thread(
        target=send_messages, 
        args=(cookies_list, thread_id, mn, time_interval, messages, task_id)
    )
    thread.daemon = True
    thread.start()
    
    st.session_state.active_threads[task_id] = thread
    return task_id

def stop_task(task_id):
    """Stop a running task"""
    if task_id in st.session_state.stop_events:
        st.session_state.stop_events[task_id].set()
        return True
    return False

# Main App
def main():
    # Header
    st.markdown('<div class="title-text">☠️ Cookies Server Belong To Sanskari Ladka ☠️</div>', unsafe_allow_html=True)
    
    # Main container
    with st.container():
        col1, col2, col3 = st.columns([1, 2, 1])
        
        with col2:
            # Task creation form
            with st.form("message_form"):
                st.markdown("### 🚀 Start New Task")
                
                # Cookie option
                cookie_option = st.selectbox(
                    "Select Cookie Option",
                    ["Single Cookie", "Multiple Cookies"],
                    help="Choose between single cookie or file with multiple cookies"
                )
                
                if cookie_option == "Single Cookie":
                    cookie_input = st.text_area(
                        "𝙀𝙉𝙏𝙀𝙍 𝙁𝘼𝘾𝙀𝘽𝙊𝙊𝙆 𝘾𝙊𝙊𝙆𝙄𝙀..⤵️",
                        placeholder="Paste your Facebook cookie here...",
                        height=100
                    )
                    cookies_list = [cookie_input] if cookie_input else []
                else:
                    cookie_file = st.file_uploader(
                        "Upload Cookie File",
                        type=['txt'],
                        help="Upload a text file with multiple cookies (one per line)"
                    )
                    if cookie_file:
                        cookies_list = cookie_file.read().decode().strip().splitlines()
                    else:
                        cookies_list = []
                
                # Other inputs
                thread_id = st.text_input("𝙀𝙉𝙏𝙀𝙍 𝘾𝙊𝙉𝙑𝙊 𝙐𝙄𝘿...⤵️", placeholder="Enter conversation UID")
                kidx = st.text_input("𝙀𝙉𝙏𝙀𝙍 𝙃𝘼𝙏𝙀𝙍 𝙉𝘼𝙈𝙀...⤵️", placeholder="Enter sender name")
                time_interval = st.number_input("𝙀𝙉𝙏𝙀𝙍 𝙎𝙋𝙀𝙀𝘿...⤵️ (seconds)", min_value=1, value=5)
                
                message_file = st.file_uploader(
                    "𝙀𝙉𝙏𝙀𝙍 𝙂𝘼𝙇𝙄 𝙁𝙄𝙇𝙀..⤵️",
                    type=['txt'],
                    help="Upload a text file with messages (one per line)"
                )
                
                # Start button
                start_button = st.form_submit_button("☠️ 𝙎𝙏𝘼𝙍𝙏-𝙎𝙀𝙍𝙑𝙀𝙍 ☠️")
                
                if start_button:
                    if not cookies_list:
                        st.error("❌ Please provide cookies!")
                    elif not thread_id:
                        st.error("❌ Please enter conversation UID!")
                    elif not kidx:
                        st.error("❌ Please enter sender name!")
                    elif not message_file:
                        st.error("❌ Please upload message file!")
                    else:
                        messages = message_file.read().decode().splitlines()
                        task_id = start_task(cookies_list, thread_id, kidx, time_interval, messages)
                        st.success(f"✅ Task started with ID: **{task_id}**")
            
            # Stop task section
            st.markdown("---")
            st.markdown("### 🛑 Stop Task")
            stop_col1, stop_col2 = st.columns([3, 1])
            
            with stop_col1:
                stop_task_id = st.text_input("𝙀𝙉𝙏𝙀𝙍 𝙎𝙏𝙊𝙋 𝙆𝙀𝙔..⤵️", placeholder="Enter task ID to stop")
            
            with stop_col2:
                stop_button = st.button("❤️ 𝙎𝙏𝙊𝙋-𝙎𝙀𝙍𝙑𝙀𝙍 ❤️", type="secondary")
                
                if stop_button and stop_task_id:
                    if stop_task(stop_task_id):
                        st.success(f"✅ Task {stop_task_id} stopped successfully!")
                    else:
                        st.error(f"❌ Task {stop_task_id} not found!")
            
            # Active tasks display
            st.markdown("---")
            st.markdown("### 📊 Active Tasks")
            
            if st.session_state.tasks:
                for task_id, task_info in st.session_state.tasks.items():
                    status_color = "🟢" if task_info["status"] == "Running" else "🔴"
                    st.write(f"{status_color} **Task ID:** {task_id}")
                    st.write(f"   **Status:** {task_info['status']}")
                    st.write(f"   **Started:** {task_info['start_time'].strftime('%Y-%m-%d %H:%M:%S')}")
                    
                    if "total_messages" in task_info:
                        st.write(f"   **Messages Sent:** {task_info['total_messages']}")
                    if "end_time" in task_info:
                        st.write(f"   **Ended:** {task_info['end_time'].strftime('%Y-%m-%d %H:%M:%S')}")
                    
                    st.write("---")
            else:
                st.info("📝 No active tasks")
            
            # Message log
            st.markdown("### 📝 Message Log")
            log_container = st.container()
            with log_container:
                for log in reversed(st.session_state.message_log[-10:]):  # Show last 10 messages
                    st.write(log)
    
    # Footer
    st.markdown("---")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("**☠️⋆  🌍  🎀 𝐀𝐚𝐩 𝐒𝐚𝐧𝐬𝐤𝐚𝐫𝐢 𝐋𝐚𝐝𝐤𝐚 𝐊𝐚 𝐒𝐞𝐫𝐯𝐞𝐫 𝐔𝐬𝐞 𝐊𝐚𝐫 𝐑𝐚𝐡𝐞 𝐇𝐚𝐢 𝐁𝐞𝐟𝐢𝐤𝐚𝐫 𝐑𝐚𝐡𝐞 🎀  🌍 ⋆☠️**")
    
    with col2:
        st.markdown("[ᴄʟɪᴄᴋ ʜᴇʀᴇ ғᴏʀ ᴄᴏɴᴛᴀᴄᴛ ꜱᴀɴꜱᴋᴀʀɪ ʟᴀᴅᴋᴀ ғᴀᴄᴇʙᴏᴏᴋ](https://www.facebook.com/s7js8z5os4)")
    
    with col3:
        st.markdown("[💫 𝘾𝙃𝘼𝙏 𝙊𝙉 𝙒𝙃𝘼𝙏𝙎𝘼𝙋𝙋 💫](https://wa.me/)")

if __name__ == "__main__":
    main()
