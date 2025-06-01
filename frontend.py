import streamlit as st
from backend import ChatbotBackend

# Initialize session state
if 'chatbot' not in st.session_state:
    st.session_state.chatbot = ChatbotBackend()

if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []

# Set page config
st.set_page_config(
    page_title="Lendeb Club AI Assistant",
    page_icon="🤖",
    layout="wide"
)

# Custom CSS
st.markdown("""
<style>
    .chat-message {
        padding: 1.5rem;
        border-radius: 0.5rem;
        margin-bottom: 1rem;
        display: flex;
        flex-direction: column;
    }
    .chat-message.user {
        background-color: #2b313e;
    }
    .chat-message.assistant {
        background-color: #475063;
    }
    .chat-message .content {
        display: flex;
        flex-direction: row;
        align-items: flex-start;
    }
    .chat-message .avatar {
        width: 2rem;
        height: 2rem;
        margin-right: 1rem;
    }
    .chat-message .message {
        flex: 1;
    }
    .stButton button {
        width: 100%;
    }
</style>
""", unsafe_allow_html=True)

# Title
st.title("🤖 Lendeb Club AI Assistant")

# Sidebar
with st.sidebar:
    st.header("About")
    st.write("""
    This AI assistant can help you with:
    - Company information
    - Product details
    - Policies and procedures
    - Terms and conditions
    - And more!
    """)

# Chat interface
for message in st.session_state.chat_history:
    with st.chat_message(message["role"]):
        st.write(message["content"])
        if message.get("tool_used"):
            st.caption(f"Tool used: {message['tool_used']}")
            if message.get("tool_reason"):
                st.caption(f"Reason: {message['tool_reason']}")

# Chat input
if prompt := st.chat_input("Ask me anything about Lendeb Club..."):
    # Add user message to chat history
    st.session_state.chat_history.append({"role": "user", "content": prompt})
    
    # Get response from chatbot
    with st.chat_message("user"):
        st.write(prompt)
    
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            response = st.session_state.chatbot.process_query(prompt)
            st.write(response["response"])
            st.caption(f"Tool used: {response['tool_used']}")
            if response.get("tool_reason"):
                st.caption(f"Reason: {response['tool_reason']}")
            
            # Add assistant message to chat history
            st.session_state.chat_history.append({
                "role": "assistant",
                "content": response["response"],
                "tool_used": response["tool_used"],
                "tool_reason": response.get("tool_reason", "")
            }) 