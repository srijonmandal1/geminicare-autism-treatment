import streamlit as st
import hashlib
import base64
import numpy as np
import sqlite3
import pandas as pd
from streamlit import session_state
from streamlit_modal import Modal
import streamlit.components.v1 as components
import vertexai
from vertexai.generative_models import GenerationConfig, GenerativeModel, Part, SafetySetting 
import vertexai.preview.generative_models as generative_models    
from io import StringIO
import logging
import sys
import os
# from dotenv import load_dotenv

# Installation Requirements
# streamlit, streamlit_modal, vertex-ai

#load_dotenv() # will search for .env file in local folder and load variables 
#api_key_string = os.getenv('api_key_string')
# TODO - Read from Env file
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "keys/geminicare-146c7a66ce3e.json"

# TODO - Read from a Property file
project_id="geminicare"
vertexai.init(project=project_id, location="us-central1")
model = GenerativeModel("gemini-1.5-flash-001")
# Set model parameters
generation_config = GenerationConfig(
    temperature=0,
    top_p=0,
    max_output_tokens=8192,
)

safety_settings = [
    SafetySetting(
        category=SafetySetting.HarmCategory.HARM_CATEGORY_HATE_SPEECH,
        threshold=SafetySetting.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE
    ),
    SafetySetting(
        category=SafetySetting.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
        threshold=SafetySetting.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE
    ),
    SafetySetting(
        category=SafetySetting.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
        threshold=SafetySetting.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE
    ),
    SafetySetting(
        category=SafetySetting.HarmCategory.HARM_CATEGORY_HARASSMENT,
        threshold=SafetySetting.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE
    ),
]

# TODO - Read this from a Database Table

patients_info = {
    "Emily": {
        "Fullname": "********",
        "Age": 35,
        "Gender": "Female",
        "Location": "Austin, TX",
        "Medical History": "History of depression",
        "Doctor Notes": "(Date: Mar 10, 2024) Patient Emily, a 35-year-old female, presents with a stable mental health condition. No significant medical history was reported. Patient displays consistent adherence to treatment regimen and demonstrates positive response to therapy. Regular check-ups are advised to monitor progress and ensure continued stability.",
        "Medical Tests Performed": "CT",
        "Family Members with Condition": 1
    },
    "Ander": {
        "Fullname": "********",
        "Age": 42,
        "Gender": "Male",
        "Location": "San Jose, CA",
        "Medical History": "History of Disorganized speech",
        "Doctor Notes": "(Date: Mar 19, 2024) Patient Ander, a 42-year-old male, has a history of depression. Current treatment regimen includes antidepressant medication and regular psychotherapy sessions. Patient's condition is stable with noticeable improvement in mood and overall well-being. Continued medication and therapy are recommended to maintain stability and prevent relapse.",
        "Medical Tests Performed": "MRI",
        "Family Members with Condition": 2
    },
    "Jack": {
        "Fullname": "********",
        "Age": 28,
        "Gender": "Male",
        "Location": "Seatle, WA",
        "Medical History": "No significant medical history",
        "Doctor Notes": "(Date: April 5, 2024) Patient Jack, a 28-year-old male, presents as a new case. No significant medical history reported. Further evaluation is required to assess symptoms and formulate an appropriate treatment plan. Patient will undergo comprehensive assessment to determine diagnosis and develop tailored intervention strategies.",
        "Medical Tests Performed": "None",
        "Family Members with Condition": 0
    },
    "Prab": {
        "Fullname": "********",
        "Age": 50,
        "Gender": "Male",
        "Location": "Bangalore, India",
        "Medical History": "Diabetes, hypertension",
        "Doctor Notes":"(Date: April 21, 2024) Patient Prab, a 50-year-old male, has a medical history of diabetes and hypertension. Both conditions are well-managed with appropriate medication and lifestyle modifications. Despite comorbidities, patient demonstrates good mental health with no significant psychiatric symptoms reported. Regular monitoring of both physical and mental health parameters is recommended to ensure optimal overall well-being.",
        "Medical Tests Performed": "None",
        "Family Members with Condition": 3
    }
}

@st.cache_data
def get_img_as_base64(file):
    with open(file, "rb") as f:
        data = f.read()
    return base64.b64encode(data).decode()

page_bg_img = f"""
<style>
[data-testid="stAppViewContainer"] > .main {{
background-image: url("")
background-position: top left;
background-repeat: no-repeat;
background-attachment: local;
}}

[data-testid="stSidebar"] > div:first-child {{

background-position: center; 
background-repeat: no-repeat;
background-attachment: fixed;
}}

[data-testid="stHeader"] {{
background: rgba(0,0,0,0);
}}

[data-testid="stToolbar"] {{
right: 2rem;
}}
</style>
"""

st.markdown(page_bg_img, unsafe_allow_html=True)

def create_table():
    conn = sqlite3.connect('user_accounts.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE, password TEXT)''')
    conn.commit()
    conn.close()

# Function to insert a new user account into the database
def insert_user(username, password):
    conn = sqlite3.connect('user_accounts.db')
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO users (username, password) VALUES (?, ?)", (username, hashlib.sha256(password.encode()).hexdigest()))
    conn.commit()
    conn.close()

# Function to check if a username exists in the database
def username_exists(username):
    conn = sqlite3.connect('user_accounts.db')
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE username=?", (username,))
    result = c.fetchone()
    conn.close()
    return result is not None

# Function to validate login credentials
def validate_login(username, password):
    if (username == "admin" and password == "Admin@1234"):
        return "admin"
    else:
        return "invalid_user"
    #conn = sqlite3.connect('user_accounts.db')
    #c = conn.cursor()
    #c.execute("SELECT * FROM users WHERE username=? AND password=?", (username, hashlib.sha256(password.encode()).hexdigest()))
    #result = c.fetchone()
    #conn.close()
    #return result is not None
    
# Function to create a SQLite database and table for storing user details
def create_details_table():
    conn = sqlite3.connect('user_details.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS user_details
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE, name TEXT)''')
    conn.commit()
    conn.close()

# Function to insert or update user details in the database
def insert_user_details(username, name):
    conn = sqlite3.connect('user_details.db')
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO user_details (username, name) VALUES (?, ?)", (username, name))
    conn.commit()
    conn.close()

# Function to retrieve user details from the database
def get_user_details(username):
    conn = sqlite3.connect('user_details.db')
    c = conn.cursor()
    c.execute("SELECT name FROM user_details WHERE username=?", (username,))
    result = c.fetchone()
    conn.close()
    return result[0] if result else None

# Main function to run the application
def main():

    create_table()
    create_details_table()

    # Initialize session state variables
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
        st.session_state.username = ""
        st.session_state.name = ""
        #st.session_state.selected_page = "Home"

    if not st.session_state.logged_in:
        
        image_url = "images/login_page_home_page_second_image.jpg"
        #col1, col2 = st.columns([1, 3])
        col1, col2 = st.columns(2)  
        with col1:
            st.image(image_url, width=450)

        with col2:
            # st.title("Login Page")
            # Using Markdown syntax to center align the title
            st.markdown("<h1 style='text-align: center;'>Log in</h1>", unsafe_allow_html=True)
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            username = "admin"
            password = "Admin@1234"
            # Using columns to create a layout with two columns
            col1, col2 = st.columns(2)

            # Adding buttons to the columns
            with col1:
                button1 = st.button("Log In")

            with col2:
                button2 = st.button("Sign up")

            if button1:
                if validate_login(username, password) == "admin":
                    st.session_state.logged_in = True
                    st.session_state.username = username
                    st.session_state.name = get_user_details(username)
                    st.success("Logged in as {}".format(username))
                    st.write("Credentials verified. Please enter Login again to continue")
                else:
                    st.error("Invalid username or password")
            if button2:
                st.title("Sign Up Page")
                new_username = st.text_input("New Username")
                new_password = st.text_input("New Password", type="password")
                if st.button("Create Account"):
                    if username_exists(new_username):
                        st.error("Username already exists. Please choose a different one.")
                    else:
                        insert_user(new_username, new_password)
                        st.success("Account created successfully!")
                        st.write("Now you can go back to the login page and log in with your new account.")

    else:
        # Display restricted content only for logged-in users
        st.sidebar.title("Navigation")
        # Page selection

        # Page selection
        #selected_page = st.sidebar.radio("Go to:", ("Home", "Info","Analyze","Ethical Guidelines", "New Patient"), key="sidebar_radio_" + st.session_state.selected_page)

        selected_page = st.sidebar.radio("Pages:", ("Home", "Patient Registration","Patient Diagnosis","Ethical Guidelines", "KnowledgeBase"))

        # Store the selected page in session state
        st.session_state.selected_page = selected_page
      
        #page = st.sidebar.radio("Go to", ["Home","Info","Analyze","Ethical Guidelines","New Patient"], key="sidebar_radio_" + st.session_state.get("page", "Home"))
        # Store the selected page in session state
        #st.session_state.page = page

        if selected_page == "Home":
            display_home()
        elif selected_page == "KnowledgeBase":
            display_info()
        elif selected_page == "Patient Diagnosis": 
            display_analysis()
        elif selected_page =="Ethical Guidelines":
            display_ethical_guidelines()
        #else:
        elif selected_page =="Patient Registration":
           add_patient()
           
            
def insert_patient_info(name, fullname, age, gender, location, history, tests, family_members):
    conn = sqlite3.connect('patients.db')  # Replace 'patients.db' with your database file path
    c = conn.cursor()
    c.execute("INSERT INTO patients (name, fullname, age, gender, location, history, tests, family_members) VALUES (?, ?, ?, ?)", (name, fullname, age, gender, location, history, tests, family_members))
    conn.commit()
    conn.close()

@st.dialog("Chat with Virtual Agent")
def chat_dialog():
    st.image("images/chat_with_an_agent.jpg")
    if st.button("Close"):
        st.rerun()

def show_dialog():
    print("Hello")
    """
            if 'openmodal' not in st.session_state:
                st.session_state.openmodal = False
            
            modal = Modal("Demo Modal", key="demo-modal",padding=20,max_width=100)
            open_modal = st.button("Live Chat")
            if open_modal:
                st.session_state.openmodal = True
            if st.session_state.openmodal:
                modal.open()

            if modal.is_open():
                with modal.container():

                    html_string = '''
                    <h1>Welcome to Virtual Assistant</h1>
                    <script language="javascript">
                      document.querySelector("h1").style.color = "brown";
                    </script>
                    <img src="../images/ms-imagine-pic5.png"
                    '''
                    components.html(html_string)
                    st.write("Some fancy text")
                    st.markdown('content')
     """


def display_home():
    #st.title("GeminiCare")
    # st.image("images/all_pages_first_image.jpg", width=700)
    st.write("Welcome back!")
    st.text("This is a tool developed for Google AI Hackathon 2024 (ai.google.dev/competition)")
    # Using columns to create a layout with two columns
    col1, col2 = st.columns(2)

    # Adding buttons to the columns
    with col1:
        st.write("")
        st.image("images/login_page_home_page_second_image.jpg", width = 400)

    with col2:
        st.write("")
        # st.write("")
        st.markdown("**What is Autism?**") 
        st.write("")
        st.write("Autism is a complex and chronic mental health disorder marked by symptoms such as delusions, hallucinations, disorganized thinking and impaired social functioning, often co-occurs with depression, anxiety disorders, and substance abuse. ")
        st.write("The symptoms not only significantly impact individual’s functioning of daily life, but also pose a risk of harm to others.")
        st.write("Early intervention, comprehensive treatment approaches, and support from healthcare professionals, family, and community resources are essential in addressing the needs of individuals living with Autism.")
        st.write("Please find more information in the information page.")
        #st.write("Autism is a mental disorder characterized by distorted thoughts, perceptions, emotions, and behaviors. It affects approximately 20 million people worldwide, making it one of the most prevalent and disabling mental illnesses globally. Despite its relatively low prevalence compared to other mental health conditions, Autism imposes a significant burden on individuals, families, and society as a whole.")
        #st.write("Autism, a severe mental disorder characterized by distorted thinking, hallucinations, and social withdrawal, poses significant challenges for individuals and families across India. Despite being a global phenomenon, the prevalence and impact of autism in India are compounded by various factors, including cultural beliefs, limited access to mental health services, and pervasive stigma. In India, where mental health remains a taboo subject, individuals living with autism often face discrimination and social isolation, exacerbating their already considerable burden. Families caring for loved ones with autism grapple with emotional distress and financial strain, as they navigate a healthcare system ill-equipped to provide adequate support. Although the Indian government has made strides in addressing mental health through initiatives like the National Mental Health Programme (NMHP) and the Mental Healthcare Act, 2017, challenges persist in translating policy into effective action, particularly at the grassroots level. Furthermore, the stigma associated with speaking out about a mental illness is high. Mental illnesses are thought by many famillies, still, are caused by the fault of the person experiencing it.")
    
    st.write("")
    st.markdown("**Current Autism Statistics:**") 
    st.image("images/autism_prevalence_stats.jpg", width=500)


    if st.button("Add Patient"):
        #print("Add Patient button clicked")  # Print statement for debugging
        st.session_state.selected_page = "New Patient"  # Update session state to navigate to "New Patient" page
        #st.query_params["selected_page"] = "New Patient"  # Update URL query parameters to navigate to "New Patient" page



    # Define the list of patients
    patients = ["Ander", "Emily", "Jack", "Pranab"]

    # Set the default selected patient
    default_index = patients.index("Ander")

    # Create the selectbox with the default selected patient
    selected_patient = st.selectbox("Select an existing patient:", patients, index=default_index, key="patient_selectbox")
    if selected_patient:
        st.subheader(f"Patient Information for {selected_patient}")

        # Store the selected patient in session state
        st.session_state.selected_patient = selected_patient

        # Using columns to create a layout with two columns
        col1, col2 = st.columns(2)

        # Adding buttons to the columns
        with col1:
            patient_info = patients_info[selected_patient]
            for field, value in patient_info.items():
                st.write(f"**{field}:** {value}")
            
        with col2:
            st.markdown("**GeminiCare Analysis:**") 
            st.write("")
            st.image("images/speech_sentiment.jpeg", width = 700)

        
        # Using columns to create a layout with two columns
        col1, col2, col3 = st.columns(3)

        # Adding buttons to the columns
        with col1:
            button1 = st.button("Update Profile")

        with col2:
            button2 = st.button("Perform Additional Diagnosis")
        with col3:
            if st.button("Live Chat"):
                chat_dialog()
            # Function to display modal
            #def display_modal():
                #st.write("This is the content of the modal.")
            #if st.button(image):
                #display_modal()
          
     
        if button1:
            updated_info = {}  # Dictionary to store updated information
            for field, value in patient_info.items():
                updated_value = st.text_input(f"Update {field}", value, key=f"{selected_patient}_{field}")
                updated_info[field] = updated_value
            # Update patient_info dictionary with updated information
            patients_info[selected_patient].update(updated_info)
            st.success("Information updated successfully!")
        elif button2:
            st.session_state.selected_page = "Analyze"

def display_info():
    st.image("images/all_pages_first_image.jpg", width=700)
    st.title("Info Page")
    #st.write("Welcome to the Info Page.")
    st.write("Understanding Autism:")
    st.markdown("**What is Autism?**") 
    "Autism, or Autism Spectrum Disorder (ASD), is a developmental condition that affects how a person communicates, interacts with others, and experiences the world around them. It is characterized by challenges in social interaction, repetitive behaviors, and restricted interests, often with unique strengths and differences in thinking and perception. Autism is a spectrum disorder, meaning it affects individuals differently and to varying degrees."

    st.markdown("**Statistics about Autism**")

    st.markdown("**Prevalence**")
    "Autism affects an estimated 1 in 100 children globally, according to the World Health Organization (WHO). It is a relatively common neurodevelopmental condition that can have a profound impact on individuals and their families. The prevalence of autism has been increasing over the years, likely due to better awareness, improved diagnostic methods, and broader definitions."

    st.markdown("**Age of Onset**")
    "Autism typically emerges in early childhood, often before the age of three. Early signs of autism may include delayed speech, limited eye contact, or difficulties in social interactions. Early detection and intervention are crucial for supporting the development of individuals with autism, although autism is a lifelong condition."
    
    st.markdown("**Global Impact**")
    "Autism affects individuals across all socioeconomic and cultural backgrounds. While autism itself is not a disability, the challenges associated with autism can lead to significant social, occupational, and personal difficulties, especially in environments that are not accommodating or inclusive."

    st.markdown("**Mortality Rate**")
    "Individuals with autism have a slightly higher mortality rate compared to the general population. This increased risk is often linked to accidents, epilepsy, and, in some cases, mental health conditions such as anxiety and depression. However, autism itself is not associated with a higher risk of mortality. Ensuring access to appropriate healthcare and support can mitigate many of these risks."

    st.markdown("**Treatment Gap**")
    "While there is no cure for autism, early intervention and tailored support can greatly improve outcomes for individuals with autism. This may include therapies such as speech therapy, occupational therapy, and behavioral interventions. However, there remains a significant gap in access to services, especially in low-resource settings, where many individuals with autism do not receive the care or support they need."

def display_analysis():
    st.image("images/all_pages_first_image.jpg", width=700)

    
    #st.title("The Model")
    #st.write("Here you will find information about the Model and App")
    
    def upload_file(file_type):
        file = st.file_uploader(f"Upload {file_type} File", type=['txt', 'csv', 'wav', 'mp4', 'mov'])
        if file:
            #submitted = st.form_submit_button("Upload")
            #if submitted:
            st.success(f"{file_type} File Uploaded Successfully!")
            #st.write(file)
            return file
        else:
            st.warning(f"Please Upload a {file_type} File.")

    def save_audio_file(uploadedFile):
        from pathlib import Path
        st.markdown("**Please upload the audio file:**")
        with st.form(key="Form :", clear_on_submit = True):
            uploadedFile = st.file_uploader(label = "Upload file", type=['wav'])
            Submit = st.form_submit_button(label='Submit')
            st.write(f"File selected: {uploadedFile.name}")
            
        st.subheader("Details : ")
        if Submit :
            st.markdown("**The file is sucessfully Uploaded.**")

            # Save uploaded file to '/home/azureuser/assets/' folder.
            save_folder = 'uploadedfiles/'
            save_path = Path(save_folder, uploadedFile.name)
            with open(save_path, mode='wb') as w:
                w.write(uploadedFile.getvalue())

            if save_path.exists():
                st.success(f'File {save_path} is successfully saved!')
            return save_path

    def analyze_audio_file():
        from pathlib import Path
        logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
        with st.form(key="Form :", clear_on_submit = False):
            uploadedFile = st.file_uploader(label = "Upload file", type=['mp4'])
            Submit = st.form_submit_button(label='Submit')
            #st.write(f"File selected: {uploadedFile.name}")
            
        if Submit :
            #st.write(f"File selected: {uploadedFile.name}")
            st.subheader("Details : ")
            st.markdown("**The file is sucessfully Uploaded.**")

            # Save uploaded file to '/home/azureuser/assets/' folder.
            save_folder = 'uploadedfiles/'
            save_path = Path(save_folder, uploadedFile.name)
            with open(save_path, mode='wb') as w:
                w.write(uploadedFile.getvalue())
            st.success(f'File {save_path} is successfully saved!')
            st.session_state.saved_filepath = save_path

        if st.button("Analyze Speech"):
            saved_filepath=st.session_state.saved_filepath
            st.write(f'Analyzing the Audio file {saved_filepath}!')
            source_path = os.path.join("",saved_filepath)
            file_name = str(saved_filepath).split("/")[-1]
            # uploadGCS(source_path, 'geminicare', 'autism_data/')

            transcription_prompt = """Please transcribe this audio file."""
            audio_file_uri = f"gs://geminicare/autism_data/{file_name}"
            st.html(f"Reading from {audio_file_uri}")
            audio_file = Part.from_uri(audio_file_uri, mime_type="audio/mp4")            
            payload = [audio_file, transcription_prompt]
            response1 = model.generate_content(payload, generation_config=generation_config, 
                                              safety_settings=safety_settings)
            transcription_text = response1.text
            print(transcription_text)
            st.html(f"<b>{transcription_text}</b>")
        
            topic_prompt = "Extract keywords in a comma separated sentence from this text:\n\n"+str(transcription_text)
            response2 = model.generate_content(topic_prompt,generation_config=generation_config, safety_settings=safety_settings)
            st.html(f"<b>Top Keywords: {response2.text}</b>")
            
            sentiment_analysis_prompt = "Please classify its sentiment as positive, negative or neutral of the following text:\n\n"+str(transcription_text)
            response3 = model.generate_content(sentiment_analysis_prompt,generation_config=generation_config, safety_settings=safety_settings)
            st.html(f"<b>Speech Sentiment: {response3.text}</b>")
            
            translation_prompt = "Please translate the following text into Spanish:\n\n"+str(transcription_text)
            response4 = model.generate_content(translation_prompt,generation_config=generation_config, safety_settings=safety_settings)
            st.html(f"<b>Text in Spanish: {response4.text}</b>")            


    def analyze_text_file(myFile):
      
        file_text = myFile.getvalue().decode()
        df = pd.read_csv(StringIO(file_text), sep='|')
        df.head()
        # st.write(file.head())

        sentiment_content_list = []

        for index, headers in df.iterrows():
            print(headers["Contents"])
            patient_text = str(headers["Contents"])
            print("Pateint Text: {}".format(patient_text))
            
            sentiment_analysis_prompt1 = "Please classify the sentiment as positive, negative or neutral of the text provided at the end and construct the sentence properly for this text:\n\n"+str(patient_text)
            response1a = model.generate_content(sentiment_analysis_prompt1,generation_config=generation_config, safety_settings=safety_settings)        
            sentiment_text = response1a.text
            
            sentiment_analysis_prompt2 = "Perform sentiment analysis and Generate html markup code with a table header 'Sentiment Analysis' and display the name of the sentiment using proper color ('Negative' in red, 'Positive' in green, 'Neutral' in blue)  and show explanation in a separate big text area for the given text and don't show the given text, only provide generated html code: \n\n" + str(sentiment_text)
            response1b = model.generate_content(sentiment_analysis_prompt2,generation_config=generation_config, safety_settings=safety_settings)        
            classified_sentiment = response1b.text.replace("```","").replace('html',"")
            
            tone_analysis_prompt1 = "Please find all the different tones and Create a JSON structure with  'tone' and 'score' where score is between 1 to 100 for this text: \n\n" + str(patient_text)          
            response2a = model.generate_content(tone_analysis_prompt1,generation_config=generation_config, safety_settings=safety_settings)
            emotional_text = response2a.text
            
            tone_analysis_prompt2 = "Generate html markup code to display the result in a html table with columns 'tone' and 'score' (which you need to load from the json structure) with header 'Tone Analysis' and show an additional column 'Explanation' and don't show the given text, only provide generated html code: \n\n" + str(emotional_text)
            response2b = model.generate_content(tone_analysis_prompt2,generation_config=generation_config, safety_settings=safety_settings)        
            emotional_tones = response2b.text.replace("```","").replace('html',"")           
            
            keyword_prompt1 = "Based on the given text, find the key intents in maximum 5 keywords: \n\n" + str(patient_text)
            response3a = model.generate_content(keyword_prompt1,generation_config=generation_config, safety_settings=safety_settings)
            intent_text = response3a.text

            keyword_prompt2 = "Generate html markup code to display the result in a html table with columns 'Intent Keyword' and 'Explanation' with table header 'Keyword Analysis' and don't show the given text, only provide generated html code: \n\n" + str(intent_text)               
            response3b = model.generate_content(keyword_prompt2,generation_config=generation_config, safety_settings=safety_settings)
            intent_keywords = response3b.text.replace("```","").replace('html',"")        
                                    
            # Append the insights result into a list.
            sentiment_content_list.append([patient_text, classified_sentiment, emotional_tones, intent_keywords])
            
        
        # Convert the list of insights into a Pandas dataframe.
        sentiment_content_df = pd.DataFrame(sentiment_content_list, columns=['patient_text', 'classified_sentiment', 'emotional_tones','intent_keywords'])
        st.html(patient_text)
        st.html(classified_sentiment)
        st.html(emotional_tones)
        st.html(intent_keywords)
        
            
    def analyze_video_file(file):

        # saved_video_filepath=st.session_state.saved_filepath
        # st.write(f'Analyzing the Video file {saved_video_filepath}!')
        # print(saved_video_filepath)

        transcription_prompt = """Please analyze the sentiment and expression in this video file. Ignore the texts and captions in the video."""
        video_file_uri = "gs://geminicare/autism_data/patient_sample_video.mp4"
        video_file = Part.from_uri(video_file_uri, mime_type="video/mp4")            
        payload = [video_file, transcription_prompt]
        response1 = model.generate_content(payload, generation_config=generation_config, 
                                          safety_settings=safety_settings)
        transcription_text = response1.text
        st.html(transcription_text)
           
       
# Title
    # Access the selected patient from session state
    selected_patient = st.session_state.selected_patient
    st.markdown(f"#### Patient Data Analysis for {selected_patient}")

# Markdown for choosing input type
    input_type = st.radio("Choose Input Type:", ('Text', 'Audio', 'Video'))
    #st.markdown(f"### You Selected {input_type} Input")

    st.write("By selecting Text, Audio or Video data about patient, I authorize the release of the information including my personal heath record and diagnosis for medical treatment and research purpose.")


# Upload file based on input type

    if input_type == 'Text':
            file = upload_file('Text')
            if st.button("Analyze User Interview"):
                analyze_text_file(file)
            #if st.checkbox("View Content"):
                #st.image("images/ms-imagine-pic1.png", width=700)
            if st.checkbox("Visual Insights"):
                st.image("images/text_analysis_insights.png", width=700)
            if st.checkbox("Patient Summary"):
                html_str3='''
                <p>This person's life has been a journey filled with struggles and triumphs as they navigate the complexities of living with autism. From a young age, he experienced feelings of isolation and misunderstanding, grappling with intrusive thoughts and overwhelming sensations that made daily tasks challenging. According to the new GeminiCare data and the data submitted on April 5th, 2024, as he entered adulthood, the symptoms of autism became more pronounced - the emotions primarily ‘Anger’ and ‘Fear’ index increased by 33% entering into adulthood, which may lead to hallucinations, delusions, and disorganized thinking dominating his reality. </p>
                <b>Recommended Treatment:</b>The patient needs therapy to re-establish courage to seek help, supported by their loved ones. The local community mental health teams (CMHTs) may also help. The medication treatment may bring some relief, but also may come with its own set of challenges, including medication side effects and the constant fear of relapse.
                '''
                st.html(html_str3)
                        
    elif input_type == 'Audio':
            # file = upload_file('Audio')
            #file_path = save_audio_file('Audio')
            #st.markdown(f"### Analyzing {file_path}")
            # Analyze uploaded file
            analyze_audio_file()
            # if st.button("Analyze User Speech"):
                # analyze_audio_file(file)
            if st.checkbox("Visual Insights"):
                st.image("images/audio_speech_analysis_insights.jpeg", width=700)
            if st.checkbox("Patient Summary"):
                html_str4='''
                <p>This person was diagnosed with Autism. The mental disorder was triggered when his parents were separated and he was left alone. His recent GeminiCare analysis shows acute onset of emotions: ‘Fear’ and ‘Sadness’. He is suffering from paranoia - a belief that everything is against him.</p>
                <b>Recommended Treatment:</b>The patient needs therapy to re-establish his positive emotions and confidence to seek help, supported by their loved ones. The FDA has approved the use of some antipsychotic drugs, such as risperidone and aripripazole, for treating irritability associated with ASD in children between certain ages. But such medication may come with its own set of challenges, including medication side effects and the constant fear of relapse. The most effective interventions available are behavioral therapies based on applied behavioral analysis (ABA).
                '''
                st.html(html_str4)
                
    elif input_type == 'Video':
            file = upload_file('Video')
            if st.button("Analyze User Expression"):
                analyze_video_file(file)
            if st.checkbox("Visual Insights"):
                st.image("images/video_analysis_insights.jpg", width=700)
            if st.checkbox("Patient Summary"):
                html_str5='''
                <p>This person is suffering from Autism. His Geminicare video analysis on April 30th, 2024 suggests significant increase in emotions - ‘Anger’ and ‘Depression’ - bizarre characterized by emotional delusions, through disorders, visual and auditory hallucinations and paranoid ideations.</p>
                <b>Recommended Treatment:</b> The most effective interventions available are behavioral therapies based on applied behavioral analysis (ABA).
                '''
                st.html(html_str5)


               
    if st.button("Live Chat"):
        chat_dialog()


def display_ethical_guidelines():
    st.image("images/all_pages_first_image.jpg", width=700)
    st.title("Ethical Guidelines")
    html_str = '''
            <!DOCTYPE html>
            <html lang="en">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>Ethical Guidelines for Apps</title>
                <style>
                    body {
                        font-family: Arial, sans-serif;
                        line-height: 1.6;
                        margin: 0;
                        padding: 20px;
                    }
                    h1 {
                        font-size: 24px;
                        margin-bottom: 20px;
                    }
                    h2 {
                        font-size: 20px;
                        margin-bottom: 10px;
                    }
                    p {
                        margin-bottom: 10px;
                    }
                    ul {
                        margin-bottom: 20px;
                    }
                    li {
                        margin-bottom: 5px;
                    }
                </style>
            </head>
            <body>
                <h1>Ethical Guidelines for Apps</h1>
                <p>We follow strict ethical guidelines. In the following, you will find the regulations we adhere by:</p>
                <p>Ethical Guidelines for apps dealing with user information, particularly concerning autism, should prioritize the well-being, privacy, and autonomy of individuals while promoting trust, transparency, and responsible data usage. Here are some key principles:</p>
                <ul>
                    <li><strong>Consent:</strong> Explicit and informed consent from users before collecting any personal information, including health-related data such as autism symptoms or treatment history.</li>
                    <li><strong>Privacy Protection:</strong> Implement robust security measures to safeguard users' data against unauthorized access, breaches, or misuse. Anonymize or pseudonymize sensitive information whenever possible to minimize the risk of re-identification.</li>
                    <li><strong>Data Minimization:</strong> Collect only the minimum amount of information necessary for the app's intended purpose. Avoid unnecessary data collection, especially concerning sensitive health information like autism.</li>
                    <li><strong>Transparency:</strong> Provide clear and accessible information about the app's data collection practices, including what types of data are collected, how they are used, and with whom they may be shared. Ensure transparency about any third-party services or partners involved in data processing.</li>
                    <li><strong>User Control:</strong> Empower users with control over their data by offering options to review, update, or delete their information. Allow users to customize their privacy settings and consent preferences.</li>
                    <li><strong>Purpose Limitation:</strong> Use user data only for the specific purposes disclosed to users and refrain from repurposing or sharing data for unrelated activities without obtaining additional consent.</li>
                    <li><strong>Data Accuracy:</strong> Take measures to ensure the accuracy and reliability of the information collected, especially when dealing with health-related data like autism symptoms or treatment outcomes.</li>
                    <li><strong>Ethical Use of AI:</strong> If the app incorporates artificial intelligence or machine learning algorithms, ensure that these technologies are used ethically and responsibly. Avoid reinforcing biases or stigmatizing behaviors related to autism.</li>
                    <li><strong>Avoid Stigmatization:</strong> Design app interfaces, content, and communications in a way that avoids stigmatizing language or imagery associated with mental health conditions, including autism. Promote a supportive and non-judgmental environment for users seeking help or information.</li>
                    <li><strong>Professional Guidance:</strong> If the app provides diagnostic or therapeutic support for autism, collaborate with mental health professionals to ensure the accuracy, safety, and ethicality of the app's content and functionalities.</li>
                    <li><strong>Accessibility:</strong> Ensure that the app is accessible to users with diverse needs, including those with autism or other mental health conditions. Provide options for customization, readability, and usability to accommodate different preferences and abilities.</li>
                    <li><strong>Continuous Evaluation:</strong> Regularly assess and evaluate the app's compliance with ethical guidelines, user feedback, and emerging best practices in data privacy and mental health support. Commit to ongoing improvement and transparency in addressing ethical concerns.</li>
                </ul>
                <p>By adhering to these ethical guidelines, apps dealing with user information, especially those related to autism, can foster trust, promote user well-being, and contribute positively to mental health care and support.</p>
            </body>
            </html>
        '''
    st.html(html_str)

# PATIENT REGISTRATION

def add_patient():
    st.image("images/all_pages_first_image.jpg", width=700)
    st.title("Add Patient")
    new_patient_name = st.text_input("Enter the name of the new patient:")
    new_patient_fullname = st.text_input("Enter the full name of the new patient:")
    new_patient_age = st.number_input("Enter the age of the new patient:", min_value=0, max_value=150)
    new_patient_gender = st.text_input("Enter the gender of the new patient:")
    new_patient_location = st.text_input("Enter the location of the new patient:")
    new_patient_history = st.text_area("Enter the medical history of the new patient:")
    new_patient_tests = st.text_input("Enter the medical tests performed of the new patient:")
    new_patient_family_members = st.number_input("Enter the number of family members with the condition:", min_value=0, max_value=100)
# Connect to SQLite database (creates a new database if it doesn't exist)
    conn = sqlite3.connect('patients.db')

# Create a cursor object to execute SQL commands
    cur = conn.cursor()

# Create the patients table if it doesn't exist
    cur.execute('''CREATE TABLE IF NOT EXISTS patients (
               id INTEGER PRIMARY KEY AUTOINCREMENT,
               name TEXT,
               fullname TEXT,
               age INTEGER,
               gender TEXT,
               location TEXT,
               history TEXT,
               tests TEXT,
               family_members INTEGER
               )''')

# Commit changes
    conn.commit()

# Close the cursor and connection
    cur.close()
    conn.close()

    st.write("By clicking on the ‘Save’ button, I authorize the release of the information including my personal heath record and diagnosis for medical treatment and research purpose.")
    if st.button("Save"):
        # Save the new patient's information to the database or storage
        insert_patient_info(new_patient_name, new_patient_fullname, new_patient_age, new_patient_gender, new_patient_location, new_patient_history, new_patient_tests, new_patient_family_members)
        st.success("New patient information saved successfully!")
        
def insert_patient(conn, name, fullname, age, gender, location, history, tests, family_members):
    """Insert a new patient into the patients table."""
    cursor = conn.cursor()
    cursor.execute('''INSERT INTO patients (name, fullname, age, gender, location, history, tests, family_members)
                      VALUES (?, ?, ?, ?)''', (name, fullname, age, gender, location, history, tests, family_members))
    conn.commit()
    cursor.close()

def get_patient_by_name(conn, name):
    """Retrieve patient information by name."""
    cursor = conn.cursor()
    cursor.execute('''SELECT * FROM patients WHERE name = ?''', (name,))
    patient_info = cursor.fetchone()
    cursor.close()
    return patient_info

# Connect to SQLite database
conn = sqlite3.connect('example.db')


if __name__ == "__main__":
    main()
