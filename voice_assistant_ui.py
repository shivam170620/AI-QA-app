import streamlit as st
import requests
import speech_recognition as sr
import base64
from PIL import Image
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# API endpoints
SEARCH_API = "http://localhost:5004/query"
INGEST_API = "http://localhost:5004/ingest-files"
INDEX_API = "http://localhost:5004/get-indexes"  # Define the endpoint to fetch collections

# Function to encode image to base64
def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode()

# Function to perform speech recognition
def speech_to_text():
    r = sr.Recognizer()
    with sr.Microphone() as source:
        st.write("Listening...")
        audio = r.listen(source)
        try:
            text = r.recognize_google(audio)
            return text
        except sr.UnknownValueError:
            return "Sorry, I couldn't understand that."
        except sr.RequestError:
            return "Sorry, there was an error with the speech recognition service."

# Encode avatars
user_avatar = encode_image("./assets/user avatar.png")
assistant_avatar = encode_image("./assets/bot avatar.jpg")

# Function to fetch collections with storage indices from the API
def get_indexes():
    try:
        response = requests.get(INDEX_API)
        if response.status_code == 200:
            return response.json()  # Return the collections list
        else:
            st.error(f"Error fetching collections: {response.text}")
            return []
    except Exception as e:
        st.error(f"Error connecting to API: {str(e)}")
        return []

def streamlit_ui():
    # Streamlit app
    st.title("AI Assistant Chat")

    # Fetch collections with storage indices
    documents = get_indexes()

    # If collections are retrieved, allow selection from a dropdown
    if documents:
        # Create a mapping of collection names to storage indices
        collections = {doc['name']: doc['storageIndex'] for doc in documents}
        selected_collection = st.selectbox("Select a collection", list(collections.keys()))
    else:
        selected_collection = None
        st.warning("No collections available.")

    # Initialize chat session
    if 'messages' not in st.session_state:
        st.session_state.messages = []

    # Sidebar for collection selection and file upload
    with st.sidebar:
        st.header("Settings")

        # Display collection storage index after selection
        storage_index = st.text_input("Index Name Input: ")

        st.header("Upload Documents")
        uploaded_files = st.file_uploader("Choose files", accept_multiple_files=True, type=['txt', 'pdf', 'md'])
        
        # Ingest files on button click
        if st.button("Ingest Files"):
            if uploaded_files and storage_index:
                files = [('files', file) for file in uploaded_files]
                response = requests.post(INGEST_API, files=files, data={'index_name': storage_index})
                if response.status_code == 200:
                    st.success("Files ingested successfully!")
                else:
                    st.error(f"Error ingesting files: {response.text}")
            else:
                st.warning("Please select a collection and upload files before ingesting.")

    # Chat window to display conversation history
    for message in st.session_state.messages:
        avatar_image = user_avatar if message["role"] == "user" else assistant_avatar
        avatar_format = "png" if message["role"] == "user" else "jpg"
        
        with st.chat_message(message["role"]):
            # Display avatar
            st.markdown(
                f'<img src="data:image/{avatar_format};base64,{avatar_image}" width="30" style="border-radius: 50%; margin-right: 10px;"/>', 
                unsafe_allow_html=True
            )
            # Display message content
            st.markdown(message["content"])

    # User input area for typing messages
    user_input = st.chat_input("Type your message here...")

    # Voice input button
    if st.button("Voice Input"):
        user_input = speech_to_text()
        if user_input not in ["Sorry, I couldn't understand that.", "Sorry, there was an error with the speech recognition service."]:
            st.text_input("Your voice input:", user_input)

    # Process user input if provided and a collection is selected
    if user_input and selected_collection:
        # Add user message to chat history
        st.session_state.messages.append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.markdown(user_input)
        
        # Send request to search API with selected collection's storage index
        response = requests.post(SEARCH_API, data={"index_name": selected_collection, "q": user_input})
        
        if response.status_code == 200:
            ai_response = response.json()["response"]
            # Add AI response to chat history
            st.session_state.messages.append({"role": "assistant", "content": ai_response})
            with st.chat_message("assistant"):
                st.markdown(ai_response)
        else:
            st.error(f"Error: {response.text}")