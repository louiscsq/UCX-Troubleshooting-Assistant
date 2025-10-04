import logging
import os
import streamlit as st
from model_serving_utils import query_endpoint, is_endpoint_supported
from ucx_utils import create_ucx_context, UCXTroubleshooter

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Ensure environment variable is set correctly
SERVING_ENDPOINT = os.getenv('SERVING_ENDPOINT')
assert SERVING_ENDPOINT, \
    ("Unable to determine serving endpoint to use for chatbot app. If developing locally, "
     "set the SERVING_ENDPOINT environment variable to the name of your serving endpoint. If "
     "deploying to a Databricks app, include a serving endpoint resource named "
     "'serving_endpoint' with CAN_QUERY permissions, as described in "
     "https://docs.databricks.com/aws/en/generative-ai/agent-framework/chat-app#deploy-the-databricks-app")

# Check if the endpoint is supported
endpoint_supported = is_endpoint_supported(SERVING_ENDPOINT)

def get_user_info():
    headers = st.context.headers
    return dict(
        user_name=headers.get("X-Forwarded-Preferred-Username"),
        user_email=headers.get("X-Forwarded-Email"),
        user_id=headers.get("X-Forwarded-User"),
    )

user_info = get_user_info()

# Streamlit app
if "visibility" not in st.session_state:
    st.session_state.visibility = "visible"
    st.session_state.disabled = False

st.title("🔧 UCX Troubleshooting Assistant")

# Add UCX-specific sidebar
with st.sidebar:
    st.header("🛠️ UCX Tools")
    
    if st.button("📋 Installation Checklist"):
        troubleshooter = UCXTroubleshooter()
        checklist = troubleshooter.get_installation_checklist()
        st.write("### Installation Checklist")
        for item in checklist:
            st.write(item)
    
    if st.button("🔍 Assessment Checklist"):
        troubleshooter = UCXTroubleshooter()
        checklist = troubleshooter.get_assessment_checklist()
        st.write("### Assessment Checklist")
        for item in checklist:
            st.write(item)
    
    if st.button("📚 Common Errors"):
        troubleshooter = UCXTroubleshooter()
        errors = troubleshooter.get_common_errors()
        st.write("### Common UCX Errors")
        for error_key, error_info in errors.items():
            with st.expander(f"🚨 {error_info['error']}"):
                st.write(f"**Solution:** {error_info['solution']}")
                st.write(f"**Details:** {error_info['details']}")

st.markdown(
    "💡 **UCX Troubleshooting Assistant** - Get help with Unity Catalog Migration issues, "
    "installation problems, and assessment errors. Just describe your issue and I'll provide specific guidance!"
)

# Check if endpoint is supported and show appropriate UI
if not endpoint_supported:
    st.error("⚠️ Unsupported Endpoint Type")
    st.markdown(
        f"The endpoint `{SERVING_ENDPOINT}` is not compatible with this basic chatbot template.\n\n"
        "This template only supports chat completions-compatible endpoints.\n\n"
        "👉 **For a richer chatbot template** that supports all conversational endpoints on Databricks, "
        "please see the [Databricks documentation](https://docs.databricks.com/aws/en/generative-ai/agent-framework/chat-app)."
    )
else:
    st.info(
        "🔧 **UCX Expert Mode Activated!** This assistant specializes in Unity Catalog Migration troubleshooting. "
        "Ask about installation issues, assessment errors, or any UCX-related problems."
    )

    # Initialize chat history
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Display chat messages from history on app rerun
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Accept user input
    if prompt := st.chat_input("Describe your UCX issue or ask any Unity Catalog migration question..."):
        # Add user message to chat history
        st.session_state.messages.append({"role": "user", "content": prompt})
        # Display user message in chat message container
        with st.chat_message("user"):
            st.markdown(prompt)

        # Display assistant response in chat message container
        with st.chat_message("assistant"):
            # Create UCX-specific context for the query
            ucx_context = create_ucx_context(prompt)
            
            # Prepare messages with UCX context
            context_message = {
                "role": "system", 
                "content": ucx_context
            }
            
            # Combine context with conversation history
            messages_with_context = [context_message] + st.session_state.messages
            
            # Query the Databricks serving endpoint
            assistant_response = query_endpoint(
                endpoint_name=SERVING_ENDPOINT,
                messages=messages_with_context,
                max_tokens=600,
            )["content"]
            st.markdown(assistant_response)


        # Add assistant response to chat history
        st.session_state.messages.append({"role": "assistant", "content": assistant_response})
