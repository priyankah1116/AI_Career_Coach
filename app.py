import streamlit as st
import os
import io
import tempfile
from datetime import datetime
from fpdf import FPDF
from fpdf.enums import XPos, YPos
from gtts import gTTS
import json
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# ✅ Streamlit input instead of argparse
user_input = st.text_input("Enter your input:")

# Configure page
st.set_page_config(
    page_title="AI Career Coach",
    page_icon="💼",
    layout="centered",
    initial_sidebar_state="expanded"
)

# Configure Google Gemini API
def get_gemini_client():
    """Get Gemini client with API key from environment or secrets"""
    api_key = None
    
    # Try to get API key from Streamlit secrets first
    try:
        if hasattr(st, 'secrets') and "GEMINI_API_KEY" in st.secrets:
            api_key = st.secrets["GEMINI_API_KEY"]
    except:
        pass
    
    # Fallback to environment variable
    if not api_key:
        api_key = os.getenv("GEMINI_API_KEY")
    
    # Fallback to session state (user input)
    if not api_key and "api_key_input" in st.session_state and st.session_state.api_key_input:
        api_key = st.session_state.api_key_input
    
    if not api_key:
        return None
        
    genai.configure(api_key=api_key)
    return genai

def call_ai(prompt, system=None, model="gemini-1.5-flash"):
    """
    Call Google Gemini API for AI responses
    """
    try:
        client = get_gemini_client()
        
        if not client:
            return "Error: No API key configured. Please add GEMINI_API_KEY to your environment or enter it in the sidebar."
        
        # Prepare the full prompt
        if system:
            full_prompt = f"{system}\n\n{prompt}"
        else:
            full_prompt = prompt
        
        # Create the model
        model_instance = genai.GenerativeModel(model)
        
        # Generate response
        response = model_instance.generate_content(
            full_prompt,
            generation_config=genai.GenerationConfig(
                temperature=0.7,
                max_output_tokens=2000,
            )
        )
        
        return response.text if response.text else "No response generated"
        
    except Exception as e:
        return f"Error: {str(e)}"

def generate_pdf(text, filename="document.pdf"):
    """Generate PDF from text content"""
    try:
        if not text or not text.strip():
            return None
            
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=10)
        
        # Clean the text and split into lines, handle Unicode characters
        clean_text = text.replace('\r', '').strip()
        # Replace common Unicode characters that cause issues
        clean_text = clean_text.replace('\u2013', '-')  # en-dash
        clean_text = clean_text.replace('\u2014', '-')  # em-dash
        clean_text = clean_text.replace('\u2018', "'")  # left single quote
        clean_text = clean_text.replace('\u2019', "'")  # right single quote
        clean_text = clean_text.replace('\u201C', '"')  # left double quote
        clean_text = clean_text.replace('\u201D', '"')  # right double quote
        clean_text = clean_text.replace('\u2022', '•')  # bullet point
        lines = clean_text.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                pdf.ln(3)  # Add some space for empty lines
                continue
                
            # Handle long lines by wrapping them
            if len(line) > 80:
                words = line.split(' ')
                current_line = ""
                for word in words:
                    if len(current_line + word + " ") < 80:
                        current_line += word + " "
                    else:
                        if current_line.strip():
                            pdf.cell(0, 5, current_line.strip(), ln=True)
                        current_line = word + " "
                if current_line.strip():
                    pdf.cell(0, 5, current_line.strip(), ln=True)
            else:
                pdf.cell(0, 5, line, ln=True)
        
        # Return PDF as bytes
        pdf_output = pdf.output(dest='S')
        if isinstance(pdf_output, str):
            return pdf_output.encode('latin-1', errors='replace')
        else:
            return bytes(pdf_output)
    except Exception as e:
        st.error(f"PDF generation error: {str(e)}")
        return None

def generate_tts(text, filename="audio.mp3"):
    """Generate text-to-speech audio file"""
    try:
        tts = gTTS(text=text, lang='en', slow=False)
        # Use temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp_file:
            tts.save(tmp_file.name)
            with open(tmp_file.name, "rb") as audio_file:
                audio_bytes = audio_file.read()
            os.unlink(tmp_file.name)  # Clean up temp file
            return audio_bytes
    except Exception as e:
        st.error(f"TTS generation error: {str(e)}")
        return None

def utility_buttons(content, content_type="document"):
    """Add utility buttons for copy, download, TTS, and like/dislike"""
    # Generate unique ID based on content length and timestamp to avoid key conflicts
    unique_id = f"{content_type}_{len(content)}_{id(content)}"
    
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        if st.button("📋 Copy", key=f"copy_{unique_id}", help="Copy to clipboard"):
            # Since direct clipboard access is limited, show content in a text area for manual copy
            st.text_area("Copy this content:", value=content, height=100, key=f"copy_area_{unique_id}")
            st.success("Content displayed above - select all and copy!")
    
    with col2:
        pdf_bytes = generate_pdf(content, f"{content_type}.pdf")
        if pdf_bytes:
            st.download_button(
                label="⬇️ PDF",
                data=pdf_bytes,
                file_name=f"{content_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
                mime="application/pdf",
                key=f"pdf_{unique_id}",
                help="Download as PDF file"
            )
        else:
            st.button("⬇️ PDF", disabled=True, help="PDF generation failed", key=f"pdf_disabled_{unique_id}")
    
    with col3:
        if st.button("🔊 TTS", key=f"tts_{unique_id}", help="Text to Speech"):
            with st.spinner("Generating audio..."):
                audio_bytes = generate_tts(content)
                if audio_bytes:
                    st.audio(audio_bytes, format="audio/mp3")
                    st.download_button(
                        label="💾 Save MP3",
                        data=audio_bytes,
                        file_name=f"{content_type}_audio_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp3",
                        mime="audio/mp3",
                        key=f"audio_{unique_id}"
                    )
    
    with col4:
        if st.button("👍", key=f"like_{unique_id}"):
            if f"likes_{content_type}" not in st.session_state:
                st.session_state[f"likes_{content_type}"] = 0
            st.session_state[f"likes_{content_type}"] += 1
            st.success("Liked! 👍")
    
    with col5:
        if st.button("👎", key=f"dislike_{unique_id}"):
            if f"dislikes_{content_type}" not in st.session_state:
                st.session_state[f"dislikes_{content_type}"] = 0
            st.session_state[f"dislikes_{content_type}"] += 1
            st.info("Feedback noted 👎")

def resume_generator():
    st.header("📄 Resume Generator")
    st.markdown("Create an ATS-friendly resume tailored to your target career - perfect for any field of study")
    
    with st.form("resume_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            name = st.text_input("Full Name *")
            email = st.text_input("Email *")
            phone = st.text_input("Phone")
            address = st.text_area("Address", height=100)
            linkedin = st.text_input("LinkedIn Profile")
        
        with col2:
            education = st.text_area("Education", height=120, help="Degree, Institution, Year, GPA (if relevant)")
            skills = st.text_area("Skills", height=120, help="List your key skills: technical, soft skills, languages, certifications, etc.")
            certifications = st.text_area("Certifications", height=120)
        
        experience = st.text_area("Work Experience", height=150, help="Include job titles, companies, dates, and key achievements")
        target_job = st.text_area("Target Job Description", height=120, help="Paste the job description you're applying for")
        
        template = st.selectbox("Resume Template", ["Simple", "Modern", "Minimal"])
        
        submitted = st.form_submit_button("Generate Resume 🚀")
    
    # Handle form submission outside the form context
    if submitted:
        if not name or not email:
            st.error("Please fill in required fields (Name and Email)")
        else:
            with st.spinner("Generating your resume..."):
                prompt = f"""
                Generate a professional, ATS-friendly resume for {name}. Use the following information:
                
                Personal Info:
                - Email: {email}
                - Phone: {phone}
                - Address: {address}
                - LinkedIn: {linkedin}
                
                Education: {education}
                Skills: {skills}
                Experience: {experience}
                Certifications: {certifications}
                
                Target Job: {target_job}
                Template Style: {template}
                
                Create a professional, one-page resume suitable for any career field with sections: Professional Summary, Skills, Experience (reverse chronological), Education, and Certifications/Awards. 
                Tailor the content to match the target job description regardless of industry (business, healthcare, education, arts, engineering, etc.). 
                Use bullet points for achievements, quantify results where possible, and highlight relevant coursework, projects, internships, or volunteer work if applicable.
                Keep it professional, concise, and ATS-friendly for all career fields. Word count: 400-600 words.
                """
                
                system_prompt = "You are an expert resume writer and career counselor with experience across all industries and career fields."
                
                resume_content = call_ai(prompt, system_prompt)
                
                if not resume_content.startswith("Error:"):
                    # Store in session state to persist across reruns
                    st.session_state.generated_resume = resume_content
                    st.success("✅ Resume generated successfully!")
                else:
                    st.error(f"Failed to generate resume: {resume_content}")
    
    # Display generated resume if it exists in session state
    if "generated_resume" in st.session_state and st.session_state.generated_resume:
        st.markdown("### Your Generated Resume:")
        st.markdown(st.session_state.generated_resume)
        
        # Add utility buttons
        utility_buttons(st.session_state.generated_resume, "resume")
        
        # Add clear button
        if st.button("🗑️ Clear Resume", key="clear_resume"):
            del st.session_state.generated_resume
            st.rerun()

def cover_letter_generator():
    st.header("📝 Cover Letter Generator")
    st.markdown("Create compelling, personalized cover letters that match job requirements")
    
    with st.form("cover_letter_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            name = st.text_input("Full Name *")
            company = st.text_input("Company Name *")
            position = st.text_input("Position Title *")
            hiring_manager = st.text_input("Hiring Manager Name (optional)")
        
        with col2:
            experience_level = st.selectbox("Experience Level", ["Entry Level", "Mid-Level", "Senior Level", "Executive"])
            tone = st.selectbox("Cover Letter Tone", ["Professional", "Enthusiastic", "Confident", "Creative"])
        
        job_description = st.text_area("Job Description", height=150, help="Paste the complete job posting")
        background = st.text_area("Your Background", height=150, help="Brief summary of your relevant experience, skills, and achievements")
        
        why_company = st.text_area("Why This Company?", height=100, help="What interests you about this specific company?")
        
        submitted = st.form_submit_button("Generate Cover Letter 🚀")
    
    # Handle form submission outside the form context
    if submitted:
        if not name or not company or not position:
            st.error("Please fill in required fields (Name, Company, Position)")
        else:
            with st.spinner("Crafting your cover letter..."):
                prompt = f"""
                Write a compelling cover letter for {name} applying for the {position} position at {company}.
                
                Applicant Details:
                - Name: {name}
                - Target Company: {company}
                - Position: {position}
                - Hiring Manager: {hiring_manager if hiring_manager else "Hiring Manager"}
                - Experience Level: {experience_level}
                - Desired Tone: {tone}
                
                Job Description: {job_description}
                
                Candidate Background: {background}
                
                Company Interest: {why_company}
                
                Create a professional cover letter that:
                1. Opens with a strong hook that demonstrates knowledge of the company
                2. Clearly connects the candidate's background to the job requirements
                3. Shows genuine enthusiasm for the role and company
                4. Includes specific examples and achievements
                5. Ends with a confident call to action
                6. Maintains the requested tone throughout
                7. Is concise (250-350 words)
                
                Format with proper business letter structure including header, date, and professional closing.
                """
                
                system_prompt = "You are a professional career advisor and expert cover letter writer with extensive experience helping candidates across all industries secure interviews."
                
                cover_letter_content = call_ai(prompt, system_prompt)
                
                if not cover_letter_content.startswith("Error:"):
                    # Store in session state to persist across reruns
                    st.session_state.generated_cover_letter = cover_letter_content
                    st.success("✅ Cover letter generated successfully!")
                else:
                    st.error(f"Failed to generate cover letter: {cover_letter_content}")
    
    # Display generated cover letter if it exists in session state
    if "generated_cover_letter" in st.session_state and st.session_state.generated_cover_letter:
        st.markdown("### Your Generated Cover Letter:")
        st.markdown(st.session_state.generated_cover_letter)
        
        # Add utility buttons
        utility_buttons(st.session_state.generated_cover_letter, "cover_letter")
        
        # Add clear button
        if st.button("🗑️ Clear Cover Letter", key="clear_cover_letter"):
            del st.session_state.generated_cover_letter
            st.rerun()

def career_advice_chat():
    st.header("💬 Career Advice Chat")
    st.markdown("Get personalized career guidance from your AI coach")
    
    # Initialize chat history
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    
    # Display chat history
    if st.session_state.chat_history:
        st.markdown("### Conversation History:")
        for i, (question, answer) in enumerate(st.session_state.chat_history):
            with st.expander(f"Q{i+1}: {question[:50]}...", expanded=False):
                st.markdown(f"**You:** {question}")
                st.markdown(f"**AI Coach:** {answer}")
                
                # Add utility buttons for each answer
                utility_buttons(answer, f"chat_{i}")
    
    # Input section
    st.markdown("### Ask Your Career Question:")
    
    # Quick topic buttons
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        if st.button("🎯 Career Change"):
            st.session_state.quick_topic = "I'm thinking about changing careers. What should I consider?"
    with col2:
        if st.button("📈 Skill Development"):
            st.session_state.quick_topic = "What skills should I develop to advance in my career?"
    with col3:
        if st.button("💰 Salary Negotiation"):
            st.session_state.quick_topic = "How can I negotiate a better salary?"
    with col4:
        if st.button("🏢 Job Search"):
            st.session_state.quick_topic = "What's the best strategy for finding a new job?"
    
    # Text input
    user_question = st.text_area(
        "Your Question:",
        value=st.session_state.get("quick_topic", ""),
        height=100,
        key="career_question",
        help="Ask anything about careers, job searching, skill development, workplace challenges, etc."
    )
    
    col1, col2 = st.columns([3, 1])
    with col1:
        # Button is always enabled, check for content inside the click handler
        if st.button("💬 Get Advice"):
            if user_question.strip():
                with st.spinner("Thinking..."):
                    prompt = f"""
                    Career question: {user_question}
                    
                    Please provide comprehensive, actionable career advice that:
                    1. Directly addresses the question
                    2. Provides specific, practical steps
                    3. Includes relevant examples or scenarios
                    4. Considers current job market trends
                    5. Offers multiple perspectives when appropriate
                    6. Is encouraging and supportive in tone
                    
                    Make the advice detailed but easy to understand and implement.
                    """
                    
                    system_prompt = "You are an experienced career counselor and coach with expertise across all industries. Provide thoughtful, practical career advice based on current best practices and market trends."
                    
                    advice = call_ai(prompt, system_prompt)
                    
                    if not advice.startswith("Error:"):
                        # Add to chat history
                        st.session_state.chat_history.append((user_question, advice))
                        
                        # Clear quick topic
                        if "quick_topic" in st.session_state:
                            del st.session_state.quick_topic
                        
                        # Refresh to show new chat
                        st.rerun()
                    else:
                        st.error(f"Failed to get advice: {advice}")
    
    with col2:
        if st.button("🗑️ Clear Chat"):
            st.session_state.chat_history = []
            if "quick_topic" in st.session_state:
                del st.session_state.quick_topic
            st.rerun()

def mock_interview():
    st.header("🎤 Mock Interview Practice")
    st.markdown("Practice interviews with AI-generated questions and get feedback on your responses")
    
    # Initialize interview session
    if "interview_questions" not in st.session_state:
        st.session_state.interview_questions = []
    if "interview_answers" not in st.session_state:
        st.session_state.interview_answers = {}
    if "current_question_index" not in st.session_state:
        st.session_state.current_question_index = 0
    
    # Interview setup
    if not st.session_state.interview_questions:
        st.markdown("### Interview Setup")
        
        with st.form("interview_setup"):
            col1, col2 = st.columns(2)
            
            with col1:
                position = st.text_input("Position Title *")
                company = st.text_input("Company Name")
                experience_level = st.selectbox("Experience Level", ["Entry Level", "Mid-Level", "Senior Level", "Executive"])
            
            with col2:
                industry = st.text_input("Industry")
                interview_type = st.selectbox("Interview Type", ["General", "Technical", "Behavioral", "Case Study"])
                num_questions = st.slider("Number of Questions", 3, 10, 5)
            
            job_description = st.text_area("Job Description (optional)", height=100)
            
            submitted = st.form_submit_button("Generate Interview Questions 🚀")
            
            if submitted:
                if not position:
                    st.error("Please provide a position title")
                else:
                    with st.spinner("Generating interview questions..."):
                        prompt = f"""
                        Generate {num_questions} interview questions for a {position} position at {company if company else "a company"}.
                        
                        Interview Details:
                        - Position: {position}
                        - Company: {company if company else "Generic Company"}
                        - Experience Level: {experience_level}
                        - Industry: {industry if industry else "General"}
                        - Interview Type: {interview_type}
                        - Job Description: {job_description if job_description else "Not provided"}
                        
                        Create a mix of questions appropriate for the role and experience level:
                        - Include both behavioral and technical questions (as relevant)
                        - Ensure questions are realistic and commonly asked
                        - Vary difficulty based on experience level
                        - Make questions specific to the role and industry when possible
                        
                        Format as a numbered list with each question on a new line.
                        """
                        
                        system_prompt = "You are an experienced HR professional and interviewer. Create realistic, relevant interview questions that help assess candidates effectively."
                        
                        questions_text = call_ai(prompt, system_prompt)
                        
                        if not questions_text.startswith("Error:"):
                            # Parse questions from the response
                            questions = []
                            for line in questions_text.split('\n'):
                                line = line.strip()
                                if line and (line[0].isdigit() or line.startswith('Q')):
                                    # Remove numbering and clean up
                                    question = line.split('.', 1)[-1].strip()
                                    if question:
                                        questions.append(question)
                            
                            st.session_state.interview_questions = questions
                            st.session_state.current_question_index = 0
                            st.session_state.interview_answers = {}
                            st.rerun()
                        else:
                            st.error(f"Failed to generate questions: {questions_text}")
    
    else:
        # Interview in progress
        st.markdown("### Interview in Progress")
        
        current_index = st.session_state.current_question_index
        total_questions = len(st.session_state.interview_questions)
        
        # Progress indicator
        progress = min(1.0, (current_index + 1) / total_questions)
        st.progress(progress, text=f"Question {current_index + 1} of {total_questions}")
        
        if current_index < total_questions:
            current_question = st.session_state.interview_questions[current_index]
            
            st.markdown(f"### Question {current_index + 1}")
            st.markdown(f"**{current_question}**")
            
            # Answer input
            answer_key = f"answer_{current_index}"
            user_answer = st.text_area(
                "Your Answer:",
                value=st.session_state.interview_answers.get(answer_key, ""),
                height=150,
                key=f"answer_input_{current_index}"
            )
            
            col1, col2, col3 = st.columns([1, 1, 2])
            
            with col1:
                if st.button("⬅️ Previous", disabled=current_index == 0):
                    if user_answer and user_answer.strip():
                        st.session_state.interview_answers[answer_key] = user_answer
                    st.session_state.current_question_index -= 1
                    st.rerun()
            
            with col2:
                if current_index < total_questions - 1:
                    if st.button("Next ➡️"):
                        if user_answer and user_answer.strip():
                            st.session_state.interview_answers[answer_key] = user_answer
                            st.session_state.current_question_index += 1
                            st.rerun()
                        else:
                            st.warning("Please provide an answer before proceeding")
                else:
                    if st.button("Finish Interview 🏁"):
                        if user_answer and user_answer.strip():
                            st.session_state.interview_answers[answer_key] = user_answer
                            st.session_state.current_question_index += 1
                            st.rerun()
                        else:
                            st.warning("Please provide an answer before finishing")
            
            with col3:
                if st.button("🔊 Read Question Aloud"):
                    audio_bytes = generate_tts(current_question)
                    if audio_bytes:
                        st.audio(audio_bytes, format="audio/mp3")
        
        else:
            # Interview completed
            st.markdown("### 🎉 Interview Completed!")
            st.markdown("Great job! Here's your interview summary and feedback:")
            
            # Generate feedback
            with st.spinner("Analyzing your responses..."):
                interview_summary = ""
                for i, question in enumerate(st.session_state.interview_questions):
                    answer = st.session_state.interview_answers.get(f"answer_{i}", "No answer provided")
                    interview_summary += f"Q{i+1}: {question}\nA{i+1}: {answer}\n\n"
                
                feedback_prompt = f"""
                Provide detailed feedback on this mock interview performance:
                
                {interview_summary}
                
                Please analyze:
                1. Overall performance assessment
                2. Strengths demonstrated in the responses
                3. Areas for improvement
                4. Specific suggestions for better answers
                5. Body language and communication tips
                6. Follow-up questions the candidate should be prepared for
                
                Provide constructive, encouraging feedback that helps the candidate improve.
                """
                
                system_prompt = "You are an experienced interview coach and HR professional. Provide detailed, constructive feedback to help candidates improve their interview performance."
                
                feedback = call_ai(feedback_prompt, system_prompt)
                
                if not feedback.startswith("Error:"):
                    st.markdown("### Interview Feedback")
                    st.markdown(feedback)
                    
                    # Utility buttons for feedback
                    utility_buttons(feedback, "interview_feedback")
                    
                    # Full interview summary
                    st.markdown("### Complete Interview Summary")
                    with st.expander("View Full Interview Q&A"):
                        st.markdown(interview_summary)
                        utility_buttons(interview_summary, "interview_summary")
                else:
                    st.error(f"Failed to generate feedback: {feedback}")
            
            # Reset button
            if st.button("🔄 Start New Interview"):
                st.session_state.interview_questions = []
                st.session_state.interview_answers = {}
                st.session_state.current_question_index = 0
                st.rerun()

def about_page():
    st.header("ℹ️ About AI Career Coach")
    
    st.markdown("""
    ### Welcome to Your AI Career Coach! 💼
    
    This comprehensive career development platform is designed to help professionals at all stages of their careers. 
    Whether you're just starting out, looking to make a career change, or aiming for that next promotion, 
    our AI-powered tools are here to guide you.
    
    ### 🛠️ Features:
    
    **📄 Resume Generator**
    - Create ATS-friendly resumes tailored to specific job descriptions
    - Multiple professional templates
    - Industry-agnostic design suitable for any career field
    - PDF export functionality
    
    **📝 Cover Letter Generator** 
    - Personalized cover letters that match job requirements
    - Customizable tone and style options
    - Company-specific content generation
    - Professional formatting
    
    **💬 Career Advice Chat**
    - Interactive AI career counselor
    - Personalized advice for career challenges
    - Conversation history tracking
    - Quick topic suggestions for common questions
    
    **🎤 Mock Interview Practice**
    - AI-generated interview questions tailored to your target role
    - Practice with realistic scenarios
    - Detailed feedback on your responses
    - Audio playback for question practice
    - Progress tracking through interview sessions
    
    ### 🎯 Additional Features:
    - **PDF Export**: Download all generated content as professional PDF documents
    - **Text-to-Speech**: Listen to questions and content for better practice
    - **Copy Functionality**: Easily copy content for use in other applications
    - **Feedback System**: Like/dislike buttons to improve AI responses
    
    ### 🔧 Technology:
    - **AI Model**: Powered by Google Gemini for intelligent, contextual responses
    - **Framework**: Built with Streamlit for a smooth, interactive experience
    - **Export Options**: FPDF for document generation, gTTS for audio synthesis
    
    ### 🚀 Getting Started:
    1. **Set up your API key**: Add your Google Gemini API key to environment variables or enter it in the sidebar
    2. **Choose a tool**: Navigate using the sidebar to access different features
    3. **Follow the prompts**: Each tool provides guided steps to generate personalized content
    4. **Download and use**: Export your generated content as PDFs or audio files
    
    ### 💡 Tips for Best Results:
    - Be specific and detailed in your inputs
    - Include relevant job descriptions when available
    - Practice regularly with the mock interview feature
    - Use the career chat for ongoing guidance and support
    
    ### 📞 Support:
    This tool is designed to be self-service, but if you encounter any issues:
    - Check your API key configuration
    - Ensure all required fields are filled out
    - Try refreshing the page if you experience any glitches
    
    **Ready to advance your career? Choose a tool from the sidebar to get started!**
    """)
    
    # API Status Check
    st.markdown("### 🔧 System Status")
    
    client = get_gemini_client()
    if client:
        if st.button("🧪 Test API Connection"):
            test_response = call_ai("Say hello in a friendly, professional way.")
            if not test_response.startswith("Error:"):
                st.success("✅ API connection successful!")
                st.info(f"Response: {test_response}")
            else:
                st.error(f"❌ API test failed: {test_response}")
    else:
        st.warning("⚠️ No API key configured. Please add your Gemini API key to get started.")

def main():
    # Initialize session state variables
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    if "interview_questions" not in st.session_state:
        st.session_state.interview_questions = []
    if "interview_answers" not in st.session_state:
        st.session_state.interview_answers = {}
    if "current_question_index" not in st.session_state:
        st.session_state.current_question_index = 0
    
    # Header
    st.title("💼 AI Career Coach")
    st.markdown("*Your AI-powered career development companion for all fields*")
    
    # Sidebar navigation
    st.sidebar.title("Navigation")
    
    # API Key configuration in sidebar
    client = get_gemini_client()
    
    if not client:
        st.sidebar.markdown("### ⚙️ API Configuration")
        st.sidebar.info("🔑 Google Gemini API key required")
        st.sidebar.markdown("""
        **Setup Instructions:**
        1. Get your free API key from [Google AI Studio](https://makersuite.google.com/app/apikey)
        2. Add it to your environment variables as `GEMINI_API_KEY`
        3. Or enter it below (temporary for this session)
        """)
        st.sidebar.text_input(
            "Gemini API Key",
            type="password",
            key="api_key_input",
            help="Enter your Google Gemini API key"
        )
        
        if st.session_state.get("api_key_input"):
            st.sidebar.success("✅ API key entered")
    else:
        st.sidebar.success("✅ Gemini API configured")
        if st.sidebar.button("🧪 Test API"):
            test_response = call_ai("Say hello in a friendly way.")
            if not test_response.startswith("Error:"):
                st.sidebar.success("✅ API connection successful!")
            else:
                st.sidebar.error(f"❌ API test failed")
    
    # Navigation menu
    page = st.sidebar.selectbox(
        "Choose a section:",
        ["Resume Generator", "Cover Letter", "Career Advice", "Mock Interview", "About"]
    )
    
    # Add some helpful info in sidebar
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 💡 Quick Tips")
    
    if page == "Resume Generator":
        st.sidebar.info("📄 Upload job descriptions for better tailoring")
    elif page == "Cover Letter":
        st.sidebar.info("📝 Research the company before generating")
    elif page == "Career Advice":
        st.sidebar.info("💬 Ask specific questions for better advice")
    elif page == "Mock Interview":
        st.sidebar.info("🎤 Practice out loud for best results")
    
    # Page routing
    if page == "Resume Generator":
        resume_generator()
    elif page == "Cover Letter":
        cover_letter_generator()
    elif page == "Career Advice":
        career_advice_chat()
    elif page == "Mock Interview":
        mock_interview()
    elif page == "About":
        about_page()

if __name__ == "__main__":
    main()