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
import re
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
import requests
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
from collections import Counter
import openai

openai.api_key = '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'
client = Groq(api_key=settings.GROQ_API_KEY)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
youtube = build('youtube', 'v3', developerKey=settings.YOUTUBE_API_KEY)
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
SEARCH_ENGINE_ID = settings.SEARCH_ENGINE_ID

def home(request):
    return render(request, 'home.html')

def voice_assistant(request):
    return render(request, 'voice_assistant.html')

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

def speak_text(text):
    """Function to read text aloud and save it as an audio file using pyttsx3."""
    pythoncom.CoInitialize()  # Initialize COM
    engine = pyttsx3.init()
    audio_file_path = os.path.join(settings.MEDIA_ROOT, 'audio', 'output.mp3')
    
    # Create directory if it doesn't exist
    os.makedirs(os.path.dirname(audio_file_path), exist_ok=True)

    engine.save_to_file(text, audio_file_path)
    engine.runAndWait()
    
    return audio_file_path


@login_required
def ask_question(request):
    answer = ""
    video_url = ""
    document_content = ""
    question = ""
    audio_file_url = ""

    if request.method == 'POST':
        uploaded_file = request.FILES.get('document')
        question = request.POST.get("question")
        audio_filename = f"audio_{int(time.time())}.mp3"

        if uploaded_file:
            documents_dir = os.path.join(settings.MEDIA_ROOT, 'documents')
            os.makedirs(documents_dir, exist_ok=True)
            file_path = os.path.join(documents_dir, uploaded_file.name)

            with open(file_path, 'wb+') as destination:
                for chunk in uploaded_file.chunks():
                    destination.write(chunk)

            document_content = read_document(file_path, uploaded_file.name)
            print("Extracted Document Content:", document_content)

            if not document_content or "Error" in document_content:
                document_content = "No content extracted from the document."
            else:
                question = document_content
                video_query = f"{question}"
                video_url = fetch_youtube_video(video_query)
                video_url = video_url.replace('watch?v=', 'embed/')

            context = (
                f"You are a helpful assistant. "
                f"Provide a detailed, step-by-step guide on how to solve the following question or topic: {question}. "
                f"Include any relevant information."
            )

            answer = generate_answer(context)
            os.remove(file_path)

        elif question:
            context = (
                f"You are a helpful assistant. "
                f"Provide a detailed, step-by-step guide on how to solve the following question or topic: {question}. "
                f"Include any relevant information."
            )

            answer = generate_answer(context)

            video_query = f"{question}"
            video_url = fetch_youtube_video(video_query)
            video_url = video_url.replace('watch?v=', 'embed/')

        else:
            answer = "No document or question was submitted."

        # Generate audio file for the answer
        if answer:
            audio_file_path = speak_text(answer)
            if audio_file_path:
                audio_file_url = f"{settings.MEDIA_URL}audio/{audio_filename}"

        # Generate quiz questions based on the question content
        if question:  # Ensure that question is used to generate new questions
            result = generate_questions(question)  # Use question as topic

            if result:  # Check if result is not empty
                questions = result  # Assuming result is a list of question dictionaries
                request.session['questions'] = questions
                request.session['attempted_questions'] = [False] * len(questions)
                request.session['user_answers'] = [None] * len(questions)
            else:
                print("No questions generated for the provided topic.")


    return render(request, 'ask_question.html', {
        'document_content': document_content,
        'question': question,
        'answer': answer,
        'video_url': video_url,
        'audio_file_url': audio_file_url,
        'MEDIA_URL': settings.MEDIA_URL,
    })

def generate_answer(context):
    start = time.process_time()
    try:
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
    except Exception as e:
        print(f"Error generating answer: {e}")
        answer = "Error generating answer."
    end = time.process_time()
    print(f"Processing time for generation: {end - start} seconds")
    return answer

import random

# quiz related functions
def generate_quiz(request):
    questions_data = request.session.get('questions', [])

    questions = []
    for q in questions_data:
        # Ensure q is a dictionary
        if isinstance(q, dict):
            question_text = q.get('question_text', 'No question text available')
            choices = q.get('choices', [])
            questions.append({'question_text': question_text, 'choices': choices})

    # Debug: Print questions to see what is being passed to the template
    print("Questions being passed to quiz page:", questions)

    return render(request, 'quiz.html', {'questions': questions})

def generate_questions(topic):
    try:
        # Call OpenAI API to generate questions and multiple choice answers
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{
                "role": "user",
                "content": f"Generate 10 quiz questions about {topic}, with four answer options (A, B, C, D), and indicate the correct answer."
            }]
        )

        # Debug: Log the API response
        print("API Response:", response)

        # Process response to create questions
        questions_text = response['choices'][0]['message']['content'].strip()
        questions_data = questions_text.split('\n\n') 
        questions = []
        
        for data in questions_data:
            if data.strip():
                # Split question text and answer options
                parts = data.split('\n')
                if len(parts) < 6:
                    continue  # Skip if the format is not correct

                question_text = parts[0].strip()
                options = [parts[i].strip() for i in range(1, 5)] 
                
                # Extract correct answer from the last line (like "Correct: A")
                correct_answer_line = parts[5].strip()  # Assuming the correct answer line follows the options
                correct_answer = correct_answer_line.split(':')[-1].strip()  # Get the part after "Correct: "

                questions.append({
                    'question_text': question_text,
                    'choices': options,
                    'answer': correct_answer  # Store the actual correct answer option (e.g., 'A')
                })

        # Debug: Log the generated questions
        print("Generated Questions:", questions)
        
        return questions

    except Exception as e:
        print("Error during question generation:", e)
        return []

    
def submit_quiz(request):
    questions = request.session.get('questions', [])
  
    score = 0
    total_questions = len(questions)

    if request.method == 'POST':
        for idx, question in enumerate(questions):
            user_answer = request.POST.get(f'question_{idx}')
            correct_answer = question.get('answer')
            
            print(f"Question {idx}: User Answer: {user_answer}, Correct Answer: {correct_answer}")
            
            # Check if the user's answer matches the correct answer
            if user_answer is not None and user_answer.strip() == correct_answer.strip():
                score += 1
        
        # Determine the pass/fail status
        pass_threshold = total_questions / 2 
        passed = score > pass_threshold

        # Render results after the quiz is submitted
        return redirect('results', score=score, total=total_questions, passed=passed) 
    return redirect('generate_quiz')


def results(request, score, total, passed):
    passed = passed == 'True'
    return render(request, 'results.html', {
        'score': score,
        'total': total,
        'passed': passed,
        
    })

@login_required
def generate_content(request):
    # Fetch values from the session
    selected_level = request.session.get('selected_level', 'Unknown Level')
    grade_id = request.session.get('grade_id', 'Unknown Grade')
    subject_id = request.session.get('subject_id', 'Unknown Subject')

    answer = ""
    video_url = ""
    topic = ""
    image_urls = []

    if request.method == "POST":
        topic = request.POST.get("topic")  # Use topic from the form

        if topic:
            context = (
                f"You are an assistant for a school system. "
                f"The current school level is '{selected_level}', "
                f"the grade is '{grade_id}', and the subject is '{subject_id}'. "
                f"Elaborate on the topic: {topic}. "
                f"You can include any relevant information."
            )
            
            start = time.process_time()
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
            end = time.process_time()
            print(f"Processing time: {end - start} seconds")

            # Fetch the video URL based on the topic
            video_url = fetch_youtube_video(topic)
            video_url = video_url.replace('watch?v=', 'embed/')
            
            # Fetch image URLs based on the topic
            image_urls = google_image_search(GOOGLE_API_KEY, SEARCH_ENGINE_ID, topic)

        else:
            answer = "No topic was submitted."
    
    return render(request, 'generate_content.html', {
        'answer': answer,
        'video_url': video_url,
        'topic': topic,
        'image_urls': image_urls
    })

def google_image_search(api_key, cse_id, query, num_results=2):
    url = "https://www.googleapis.com/customsearch/v1"
    params = {
        'key': api_key,
        'cx': cse_id,
        'q': query,
        'searchType': 'image',
        'num': num_results
    }
    
    response = requests.get(url, params=params)
    if response.status_code == 200:
        results = response.json()
        image_urls = [item['link'] for item in results.get('items', [])]
        return image_urls
    else:
        print("Error:", response.status_code, response.text)
        return []


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
