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

client = Groq(api_key=settings.GROQ_API_KEY)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
youtube = build('youtube', 'v3', developerKey=settings.YOUTUBE_API_KEY)\

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
        # Handle document upload
        uploaded_file = request.FILES.get('document')
        question = request.POST.get("question")

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
                question = document_content  # Use the document content as the question
                video_query = f"{question}"
                video_url = fetch_youtube_video(video_query)
                video_url = video_url.replace('watch?v=', 'embed/')

        elif question:
            # Prepare context for the model
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
            audio_file_url = speak_text(answer)

        # Store the original question in the session
        if question:
            request.session['last_question'] = question  # Store original question

            # Generate quiz questions based on the original question
            difficulty_level = "easy"  # Set your desired difficulty level
            num_questions = 5  # Define the number of questions to generate
            questions, key_answers, options = generate_mcq_questions_from_question(question, difficulty_level, num_questions)

            # Store in session
            request.session['questions'] = questions
            request.session['key_answers'] = key_answers
            request.session['options'] = options

    return render(request, 'ask_question.html', {
        'document_content': document_content,
        'question': question,
        'answer': answer,
        'video_url': video_url,
        'audio_file_url': f"{settings.MEDIA_URL}audio/output.mp3",
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

def generate_related_questions(original_question):
    keywords = extract_keywords(original_question)

    if not keywords:
        return ["No related questions can be generated due to lack of keywords."]

    related_questions = []
    
    question_templates = [
        "What is the significance of {}?",
        "How is {} used in real-world applications?",
        "What are the benefits of understanding {}?",
        "Can you provide examples of {}?",
        "What challenges are associated with {}?",
        "How does {} compare to similar concepts?",
        "What future developments might impact our understanding of {}?"
    ]

    for keyword in keywords:
        # Generate questions only for valid keywords
        if keyword.lower() not in ['and', 'or', 'the', 'of', 'to', 'a']:
            for template in question_templates:
                related_questions.append(template.format(keyword))

    random.shuffle(related_questions)  # Shuffle to randomize the order
    return related_questions[:5]  # Return a limited number of unique questions

def extract_keywords(question):
    words = question.split()
    # Simple keyword extraction; can be improved with NLP techniques
    keywords = [word for word in words if len(word) > 3 and word.isalpha()]  # Filter by word length and ensure they are words
    return list(set(keywords))  # Remove duplicates

# Example usage
original_question = "What is the significance of photosynthesis?"
related_questions = generate_related_questions(original_question)
for q in related_questions:
    print(q)

def generate_mcq_questions_from_question(original_question, difficulty_level, num_questions):
    questions = []
    key_answers = []
    options_list = []

    related_questions = generate_related_questions(original_question)

    if len(related_questions) < 4:
        return [], [], []

    for _ in range(num_questions):
        correct_answer = random.choice(related_questions)

        # Create a dynamic question based on the related question
        question = generate_related_questions(correct_answer)

        # Generate plausible but incorrect answers (distractors)
        incorrect_answers = generate_incorrect_answers(related_questions, correct_answer)

        # Shuffle the options
        options = [correct_answer] + incorrect_answers
        random.shuffle(options)

        questions.append(question)
        key_answers.append(correct_answer)
        options_list.append(options)

    return questions, key_answers, options_list

def generate_incorrect_answers(all_concepts, correct_answer):
    potential_distractors = [concept for concept in all_concepts if concept != correct_answer]
    if len(potential_distractors) < 3:
        return potential_distractors  # Not enough for distractors
    incorrect_answers = random.sample(potential_distractors, 3)
    return incorrect_answers

def quiz(request):
    questions = request.session.get('questions', [])
    options = request.session.get('options', [])
    key_answers = request.session.get('key_answers', [])

    prepared_questions = list(zip(questions, options))

    if 'attempted_questions' not in request.session:
        request.session['attempted_questions'] = [False] * len(prepared_questions)

    if request.method == "POST":
        user_answers = []
        for i in range(len(prepared_questions)):
            user_answer = request.POST.get(f'question_{i+1}')
            user_answers.append(user_answer)
            request.session['attempted_questions'][i] = user_answer is not None

        request.session['user_answers'] = user_answers
        request.session['submitted'] = True

        return redirect('results')

    return render(request, 'generate_quiz.html', {
        'questions': prepared_questions,
    })

def results(request):
    user_answers = request.session.get('user_answers', [])
    key_answers = request.session.get('key_answers', [])
    attempted_questions = request.session.get('attempted_questions', [])
    questions = request.session.get('questions', [])

    if not user_answers or not key_answers or not questions:
        print("One of the lists is empty: ", user_answers, key_answers, questions)

    score = sum(1 for i in range(len(user_answers)) if user_answers[i] == key_answers[i] and attempted_questions[i])
    total_questions = len(attempted_questions)

    results = []
    for i in range(len(user_answers)):
        results.append((questions[i], user_answers[i], key_answers[i]))

    context = {
        'score': score,
        'total_questions': total_questions,
        'results': results,
    }

    # Clear only quiz-related session data
    request.session['questions'] = []
    request.session['options'] = []
    request.session['attempted_questions'] = []
    request.session['user_answers'] = []
    request.session['submitted'] = False
    request.session['key_answers'] = []

    return render(request, 'submit_quiz.html', context)

# content page functions 

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

            # Fetch images based on the topic
            image_urls = fetch_images_from_serper(topic)  # Use topic instead of selected_topic

            # Store the answer in the session for later use
            request.session['generated_answer'] = answer

            # Fetch the video URL based on the topic
            video_query = topic  # Use topic for video fetching
            video_url = fetch_youtube_video(video_query)
            video_url = video_url.replace('watch?v=', 'embed/')
        else:
            answer = "No topic was submitted."
    
    return render(request, 'generate_content.html', {'answer': answer, 'video_url': video_url, 'topic': topic, 'image_urls': image_urls})

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

# Define a mapping of subjects to potential keywords
SUBJECT_KEYWORDS = {
    "Mathematics": ["fractions", "geometry", "algebra", "addition", "subtraction", "shapes", "Count to 100", "number line", "Write the date", "time", "Identify", "sort","classify"],
    "English": ["grammar", "nouns", "verbs", "adjectives", "sentences", "punctuation", "Phonics & Spelling", "Handwriting and Writing"],
    "Science": ["biology", "chemistry", "physics", "experiments"],
    "History": ["ancient", "medieval", "modern", "events"],
    
}

def extract_keywords_for_image_query(answer, subject):
    # Remove special characters and split the answer into words
    words = re.findall(r'\b\w+\b', answer.lower())
    
    # Create a frequency count of words
    word_counts = Counter(words)
    
    # Get relevant keywords based on the subject
    relevant_keywords = SUBJECT_KEYWORDS.get(subject, [])
    
    # Find relevant keywords in the answer
    keywords = [word for word in relevant_keywords if word in word_counts]
    
    # Formulate a query string
    return " and ".join(keywords) if keywords else "education"

def fetch_images_from_serper(query):
    api_key = settings.SERPER_API_KEY
    url = "https://api.serper.dev/search/images"

    params = {
        "q": query,
        "gl": "us",
        "hl": "en",
        "type": "image"
    }

    headers = {
        "Authorization": f"Bearer {api_key}"
    }

    response = requests.get(url, headers=headers, params=params)

    if response.status_code == 200:
        results = response.json()
        return [item['link'] for item in results['image_results']]
    else:
        print("Error fetching images:", response.text)
        return []