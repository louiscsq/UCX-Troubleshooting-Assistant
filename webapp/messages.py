"""
Message classes for the chatbot application.

This module contains the message classes used throughout the app.
By keeping them in a separate module, they remain stable across
Streamlit app reruns, avoiding isinstance comparison issues.
"""
import streamlit as st
import yaml
from abc import ABC, abstractmethod

# Load configuration
import os
config_file = os.getenv('CONFIG_FILE', 'configs/ucx.config.yaml')
config_path = os.path.join(os.path.dirname(__file__), config_file)
with open(config_path, 'r') as f:
    CONFIG = yaml.safe_load(f)


class Message(ABC):
    def __init__(self):
        pass

    @abstractmethod
    def to_input_messages(self):
        """Convert this message into a list of dicts suitable for the model API."""
        pass

    @abstractmethod
    def render(self, idx):
        """Render the message in the Streamlit app."""
        pass


class UserMessage(Message):
    def __init__(self, content):
        super().__init__()
        self.content = content

    def to_input_messages(self):
        return [{
            "role": "user",
            "content": self.content
        }]

    def render(self, _):
        with st.chat_message("user"):
            st.markdown(self.content)


class AssistantResponse(Message):
    def __init__(self, messages, request_id, thinking_messages=None, final_content=None, pdf_data=None, is_complete=True):
        super().__init__()
        self.messages = messages
        # Request ID tracked to enable submitting feedback on assistant responses via the feedback endpoint
        self.request_id = request_id
        # Separate thinking (tool calls/outputs) from final answer
        self.thinking_messages = thinking_messages or []
        self.final_content = final_content or ""
        # PDF data for downloadable reports (optional)
        self.pdf_data = pdf_data
        # Track completion status for proper rendering
        self.is_complete = is_complete

    def to_input_messages(self):
        return self.messages
    
    def _extract_doc_sources(self):
        """Extract unique doc_uri values from all tool responses."""
        import json
        import re
        
        doc_sources = set()
        
        for msg in self.thinking_messages:
            if msg.get("role") == "tool":
                content = msg.get("content", "")
                
                try:
                    # Try JSON first
                    data = json.loads(content)
                    if isinstance(data, list):
                        for item in data:
                            if isinstance(item, dict) and 'metadata' in item:
                                metadata = item['metadata']
                                if isinstance(metadata, dict):
                                    doc_uri = metadata.get('doc_uri')
                                    if doc_uri:
                                        doc_sources.add(doc_uri)
                except json.JSONDecodeError:
                    # Use regex to extract doc_uri values from Python-formatted string
                    doc_uri_pattern = r"'doc_uri':\s*'([^']+)'"
                    matches = re.findall(doc_uri_pattern, content)
                    for uri in matches:
                        doc_sources.add(uri)
                except Exception:
                    pass
        
        return doc_sources

    def render(self, idx):
        with st.chat_message("assistant"):
            # If we have separated thinking/final content, render them separately
            if self.thinking_messages or self.final_content:
                # Show thinking section if we have tool calls/outputs
                if self.thinking_messages:
                    # Use "Done" label for completed responses, "Thinking" for incomplete
                    expander_label = "✅ Done" if self.is_complete else "🤔 Thinking process..."
                    thinking_container = st.expander(expander_label, expanded=False)
                    with thinking_container:
                        for msg in self.thinking_messages:
                            render_message(msg)
                
                # Show final answer
                if self.final_content:
                    st.markdown(self.final_content)
                
                # Extract and show document sources from tool outputs
                doc_sources = self._extract_doc_sources()
                
                if doc_sources:
                    st.markdown("---")
                    st.markdown("📚 **Sources:**")
                    
                    if len(doc_sources) == 1:
                        source = list(doc_sources)[0]
                        st.markdown(f"[{source}]({source})")
                    else:
                        # Use columns for horizontal layout
                        cols = st.columns(min(len(doc_sources), 3))
                        for idx, source in enumerate(sorted(doc_sources)):
                            col_idx = idx % len(cols)
                            with cols[col_idx]:
                                # Extract filename from URL for display
                                filename = source.split('/')[-1] if '/' in source else source
                                st.markdown(f"[{filename}]({source})")
            else:
                # Fallback: render all messages normally (legacy behavior)
                for msg in self.messages:
                    render_message(msg)
            
            # Add download button if PDF is available
            if self.pdf_data:
                import time
                st.markdown("---")
                
                # Compact download area
                col1, col2 = st.columns([4, 1])
                
                with col1:
                    word_count = len(self.final_content.split()) if self.final_content else 0
                    st.markdown(f"**💾 Download available** • {word_count} words • {CONFIG.get('pdf_download_label', 'Ready for documentation')}")
                
                with col2:
                    # Small icon-sized download button that persists
                    st.download_button(
                        label="📄",
                        data=self.pdf_data,
                        file_name=f"{CONFIG.get('pdf_filename_prefix', 'Response')}_{time.strftime('%Y%m%d_%H%M%S')}.pdf",
                        mime="application/pdf",
                        help="Download PDF report",
                        key=f"pdf_download_{idx}_{abs(hash(self.final_content))}",
                        type="secondary"
                    )

            if self.request_id is not None:
                render_assistant_message_feedback(idx, self.request_id)

def render_message(msg):
    """Render a single message."""
    if msg["role"] == "assistant":
        # Render content first if it exists
        if msg.get("content"):
            st.markdown(msg["content"])
        
        # Then render tool calls if they exist
        if "tool_calls" in msg and msg["tool_calls"]:
            for call in msg["tool_calls"]:
                fn_name = call["function"]["name"]
                args = call["function"]["arguments"]
                st.markdown(f"🛠️ **Calling {fn_name}**")
                st.code(args, language="json")
    elif msg["role"] == "tool":
        st.markdown("🧰 **Tool Response**")
        # Extract and show only doc_uris from the tool response
        content = msg["content"]
        try:
            import json
            # Try to parse as JSON array
            data = json.loads(content)
            if isinstance(data, list) and len(data) > 0:
                doc_uris = set()
                for item in data:
                    if isinstance(item, dict) and 'metadata' in item:
                        doc_uri = item['metadata'].get('doc_uri')
                        if doc_uri:
                            doc_uris.add(doc_uri)
                
                if doc_uris:
                    st.caption(f"Retrieved {len(data)} results from {len(doc_uris)} sources")
                    for uri in sorted(doc_uris):
                        st.caption(f"• {uri}")
                else:
                    st.caption(f"Retrieved {len(data)} results")
            else:
                st.caption("Retrieved data")
        except:
            # If not JSON, just show a summary
            st.caption(f"Retrieved {len(content)} characters of data")


@st.fragment
def render_assistant_message_feedback(i, request_id):
    """Render feedback UI for assistant messages."""
    from model_serving_utils import submit_feedback
    import os
    
    def save_feedback(index):
        serving_endpoint = os.getenv('SERVING_ENDPOINT')
        if serving_endpoint:
            submit_feedback(
                endpoint=serving_endpoint,
                request_id=request_id,
                rating=st.session_state[f"feedback_{index}"]
            )
    
    st.feedback("thumbs", key=f"feedback_{i}", on_change=save_feedback, args=[i])