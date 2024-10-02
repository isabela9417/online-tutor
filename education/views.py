from django.shortcuts import render, redirect
from .models import Grade, Subject, Question, Quiz, Performance
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
import random
from django.contrib import messages
from django.contrib.auth.models import User
from django.http import HttpResponse
from groq import Groq
import os
from dotenv import load_dotenv 
from django.conf import settings
import time
from django.http import HttpResponseBadRequest
from googleapiclient.discovery import build
from .forms import DocumentUploadForm
from PIL import Image
import pytesseract
from docx import Document
import pypdf
from gtts import gTTS
from playsound import playsound
import pyttsx3
import threading
import pythoncom
# from openai.error import RateLimitError
from langchain.docstore.document import Document
from langchain.document_loaders import TextLoader
from langchain.text_splitter import CharacterTextSplitter
from langchain.embeddings import OpenAIEmbeddings
from langchain_openai import OpenAIEmbeddings
from openai import OpenAIError
from langchain.vectorstores import FAISS
from langchain.chains import RetrievalQA
from langchain.schema import Document

client = Groq(api_key=settings.GROQ_API_KEY)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
youtube = build('youtube', 'v3', developerKey=settings.YOUTUBE_API_KEY)\

def home(request):
    return render(request, 'home.html')

def upload_assignment(request):
    return render(request, 'upload_assignment.html')

def login_view(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('select_grade')
    return render(request, 'login.html')

def signup_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')
        
        if password != confirm_password:
            messages.error(request, "Passwords do not match.")
            return render(request, 'signup.html')
        
        user = User.objects.create_user(username=username, password=password)
        login(request, user)
        return redirect('select_grade')

    return render(request, 'signup.html')

@login_required
def select_school_level(request):
    if request.method == 'POST':
        selected_level = request.POST.get('level')
        request.session['selected_level'] = selected_level
        return redirect('select_grade')
    
    return render(request, 'select_school_level.html')

@login_required
def select_grade(request):
    if 'selected_level' not in request.session:
        return redirect('select_school_level')

    if request.method == 'POST':
        grade_id = request.POST.get('grade')
        request.session['grade_id'] = grade_id
        return redirect('select_subject')
    
    selected_level = request.session['selected_level']
    grades = Grade.objects.filter(level=selected_level)
    
    return render(request, 'select_grade.html', {'grades': grades})

@login_required
def select_subject(request):
    grade_id = request.session.get('grade_id')
    if request.method == 'POST':
        subject_id = request.POST['subject']
        request.session['subject_id'] = subject_id
        return redirect('generate_content')

    subjects = Subject.objects.filter(grade_id=grade_id)
    return render(request, 'select_subject.html', {'subjects': subjects})


@login_required
def generate_quiz(request):
    question_id = request.session.get('question_id')
    question = Question.objects.get(id=question_id)
    quizzes = Quiz.objects.filter(question=question)
    if request.method == 'POST':
        selected_answer = request.POST['answer']
        correct_answer = quizzes.get(answer=selected_answer)
        user_performance, created = Performance.objects.get_or_create(user=request.user)
        user_performance.score = (user_performance.score if created else user_performance.score + (1 if correct_answer else 0))
        user_performance.save()
        return redirect('rate_performance')
    return render(request, 'generate_quiz.html', {'quizzes': quizzes})

@login_required
def rate_performance(request):
    user_performance = Performance.objects.get(user=request.user)
    feedback = "Good job!" if user_performance.score >= 5 else "Keep practicing!"
    user_performance.feedback = feedback
    user_performance.save()
    return render(request, 'rate_performance.html', {'performance': user_performance})

def fetch_youtube_video(query):
    try:
        request = youtube.search().list(
            part='snippet',
            q=query,
            type='video',
            order='relevance',
            maxResults=1
        )
        response = request.execute()
        
        items = response.get('items', [])
        if items:
            video_id = items[0]['id']['videoId']
            return f"https://www.youtube.com/watch?v={video_id}"
    except Exception as e:
        print(f"Error fetching YouTube video: {e}")
    
    return ""

# Function to read the document
def read_document(file_path, file_name):
    if file_name.lower().endswith(('.pdf')):
        return read_pdf(file_path)
    elif file_name.lower().endswith(('.docx', '.doc')):
        return read_word(file_path)
    elif file_name.lower().endswith(('.jpg', '.jpeg', '.png')):
        return read_image(file_path)
    elif file_name.lower().endswith(('.txt')):
        return read_text(file_path)
    elif file_name.lower().endswith(('.csv')):
        return read_csv(file_path)
    else:
        return "Unsupported file type."

def read_pdf(file_path):
    try:
        with open(file_path, 'rb') as pdf_file:
            pdf_reader = pypdf.PdfReader(pdf_file)
            text = ''
            for page in pdf_reader.pages:
                text += page.extract_text() or ''
            return text
    except Exception as e:
        print(f"Error reading PDF: {e}")
        return "Error reading PDF."

def read_word(file_path):
    try:
        doc = Document(file_path)
        text = '\n'.join(paragraph.text for paragraph in doc.paragraphs)
        return text
    except Exception as e:
        print(f"Error reading Word document: {e}")
        return "Error reading Word document."

def read_image(file_path):
    try:
        image = Image.open(file_path)
        text = pytesseract.image_to_string(image)
        return text
    except Exception as e:
        print(f"Error reading image: {e}")
        return "Error reading image."

def read_text(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            return file.read()
    except Exception as e:
        print(f"Error reading text file: {e}")
        return "Error reading text file."


# Assuming you have some client for chat completions
# from your_chat_client import client  # Adjust this import according to your project

def speak_text(text, filename):
    """Function to read text aloud and save it as an audio file using pyttsx3."""
    pythoncom.CoInitialize()  # Initialize COM
    engine = pyttsx3.init()
    audio_file_path = os.path.join(settings.MEDIA_ROOT, 'audio', filename)

    # Create directory if it doesn't exist
    os.makedirs(os.path.dirname(audio_file_path), exist_ok=True)

    try:
        engine.save_to_file(text, audio_file_path)
        engine.runAndWait()
    except Exception as e:
        print(f"Error saving audio file: {e}")
        return None  # Return None if there's an error

    return audio_file_path


@login_required
def ask_question(request):
    answer = ""
    video_url = ""
    document_content = ""
    question = ""
    audio_file_url = ""

    if request.method == 'POST':
        # Handle document upload
        uploaded_file = request.FILES.get('document')
        question = request.POST.get("question")

        # Generate a unique filename based on the question or document content
        audio_filename = f"audio_{int(time.time())}.mp3"

        # If a document is uploaded
        if uploaded_file:
            documents_dir = os.path.join(settings.MEDIA_ROOT, 'documents')
            os.makedirs(documents_dir, exist_ok=True)
            file_path = os.path.join(documents_dir, uploaded_file.name)

            # Save the file
            with open(file_path, 'wb+') as destination:
                for chunk in uploaded_file.chunks():
                    destination.write(chunk)

            # Read the document based on file type
            document_content = read_document(file_path, uploaded_file.name)
            print("Extracted Document Content:", document_content)

            if not document_content or "Error" in document_content:
                document_content = "No content extracted from the document."
            else:
                question = document_content
                video_query = f"{question}"
                video_url = fetch_youtube_video(video_query)
                video_url = video_url.replace('watch?v=', 'embed/')

            # Prepare context for the model without restrictions
            context = (
                f"You are a helpful assistant. "
                f"Provide a detailed, step-by-step guide on how to solve the following question or topic: {question}. "
                f"Include any relevant information."
            )

            # Generate answer using the model
            start = time.process_time()
            try:
                chat_completion = client.chat.completions.create(
                    messages=[{"role": "system", "content": "You are a helpful assistant that provides comprehensive solutions."},
                              {"role": "user", "content": context}],
                    model="llama3-8b-8192",
                    temperature=0.5,
                    max_tokens=1024,
                    top_p=1,
                    stop=None,
                    stream=False,
                )
                answer = chat_completion.choices[0].message.content
            except Exception as e:
                print(f"Error generating answer: {e}")
                answer = "Error generating answer."
            end = time.process_time()
            print(f"Processing time for document: {end - start} seconds")

            os.remove(file_path)

        elif question:
            # Prepare context for the model without restrictions
            context = (
                f"You are a helpful assistant. "
                f"Provide a detailed, step-by-step guide on how to solve the following question or topic: {question}. "
                f"Include any relevant information."
            )

            start = time.process_time()
            try:
                chat_completion = client.chat.completions.create(
                    messages=[{"role": "system", "content": "You are a helpful assistant that provides comprehensive solutions."},
                              {"role": "user", "content": context}],
                    model="llama3-8b-8192",
                    temperature=0.5,
                    max_tokens=1024,
                    top_p=1,
                    stop=None,
                    stream=False,
                )
                answer = chat_completion.choices[0].message.content
            except Exception as e:
                print(f"Error generating answer: {e}")
                answer = "Error generating answer."
            end = time.process_time()
            print(f"Processing time for question: {end - start} seconds")

            video_query = f"{question}"
            video_url = fetch_youtube_video(video_query)
            video_url = video_url.replace('watch?v=', 'embed/')

        else:
            answer = "No document or question was submitted."

        # Generate audio file for the answer
        if answer:
            audio_file_path = speak_text(answer, audio_filename)  # Pass unique filename
            if audio_file_path:
                audio_file_url = f"{settings.MEDIA_URL}audio/{audio_filename}"  # Use the unique filename

    return render(request, 'ask_question.html', {
        'document_content': document_content,
        'question': question,
        'answer': answer,
        'video_url': video_url,
        'audio_file_url': audio_file_url,  # Correctly reference the audio file
        'MEDIA_URL': settings.MEDIA_URL,  # Add MEDIA_URL to the context
    })



@login_required
def generate_content(request):
    # Fetch values from the session
    selected_level = request.session.get('selected_level', 'Unknown Level')
    grade_name = request.session.get('grade_name', 'Unknown Grade')
    subject_name = request.session.get('subject_name', 'Unknown Subject')

    grade_id = request.session.get('grade_id', 'Unknown Grade')
    subject_id = request.session.get('subject_id', 'Unknown Subject')

    answer = ""
    video_url = ""
    audio_file_url = ""

    if request.method == "POST":
        selected_topic = request.POST.get("topic")

        # Generate a unique filename for the audio
        audio_filename = f"audio_{int(time.time())}.mp3"

        if selected_topic:
            context = (
                f"You are an assistant for a school system. "
                f"The current school level is '{selected_level}', "
                f"the grade is '{grade_id}', and the subject is '{subject_id}'. "
                f"Elaborate on the topic: {selected_topic}. "
                f"You can include any relevant information."
            )
            
            start = time.process_time()
            chat_completion = client.chat.completions.create(
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that provides comprehensive solutions."},
                    {"role": "user", "content": context}
                ],
                model="llama3-8b-8192",
                temperature=0.5,
                max_tokens=1024,
                top_p=1,
                stop=None,
                stream=False,
            )
            answer = chat_completion.choices[0].message.content
            end = time.process_time()
            print(f"Processing time: {end - start} seconds")

            # Generate audio for the answer
            audio_file_path = speak_text(answer, audio_filename)  # Pass unique filename
            if audio_file_path:
                audio_file_url = f"{settings.MEDIA_URL}audio/{audio_filename}"  # Use the unique filename

            # Fetch the video URL based on the topic
            video_query = selected_topic
            video_url = fetch_youtube_video(video_query)
            video_url = video_url.replace('watch?v=', 'embed/')
        else:
            answer = "No topic was submitted."
    
    return render(request, 'generate_content.html', {
        'answer': answer,
        'video_url': video_url,
        'audio_file_url': audio_file_url,  # Pass the audio file URL to the template
    })


def is_valid_answer(answer, selected_level, grade_name, subject_name):
    if selected_level in answer and grade_name in answer and subject_name in answer:
        return True
    return False


def is_valid_answer(answer, selected_level, grade_id, subject_id):
    """
    Validate if the answer is relevant to the specified level, grade, and subject.
    This is a placeholder function and should be implemented based on specific criteria.
    """
    if not answer:
        return False

    if (selected_level.lower() in answer.lower() or 
        grade_id.lower() in answer.lower() or 
        subject_id.lower() in answer.lower()):
        return True

    return False


def generate_questions(document_text):
    response = requests.post(
        'https://api.groq.com/generate-questions',
        headers={
            'Content-Type': 'application/json',
            'Authorization': f'Bearer client',
        },
        json={'text': document_text}
    )
    try:
        questions = generate_questions(document_text)
    except Exception as e:
        print(f"Error generating questions: {e}")

    return response.json().get('questions', [])

