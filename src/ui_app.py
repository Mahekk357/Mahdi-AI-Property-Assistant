import streamlit as st
from src.vectorstore_setup import load_vectorstore
from src.agent import *
from langchain_core.messages import HumanMessage, AIMessage

def main():
    st.title("🏙️ Mahdi AI Property Assistant")
    st.write("Ask about property listings, rent, or area comparisons.")

    # Initialize session state for conversation history
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Initialize agent (cached across reruns)
    if "agent" not in st.session_state:
        store = load_vectorstore()
        st.session_state.agent = init_agent()

    # Display chat history
    for message in st.session_state.messages:
        if isinstance(message, HumanMessage):
            with st.chat_message("user"):
                st.markdown(message.content)
        elif isinstance(message, AIMessage):
            with st.chat_message("assistant"):
                st.markdown(message.content)

    # Handle new user input
    user_input = st.chat_input("Ask a question...")
    if user_input:
        # Display user message immediately
        with st.chat_message("user"):
            st.markdown(user_input)

        # Add user message to history
        st.session_state.messages.append(HumanMessage(content=user_input))

        # Get agent response with full conversation history
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                response = chat_with_agent(
                    st.session_state.agent,
                    user_input,
                    history=st.session_state.messages[:-1]  # Exclude the just-added user message
                )
            st.markdown(response)

        # Add assistant response to history
        st.session_state.messages.append(AIMessage(content=response))

if __name__ == "__main__":
    main()
