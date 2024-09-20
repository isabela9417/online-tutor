from django.shortcuts import render, redirect
from .models import Grade, Subject, Question, Quiz, Performance
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
import random
from django.contrib import messages
from django.contrib.auth.models import User
from django.shortcuts import render
from django.http import HttpResponse
from groq import Groq
import os
from django.conf import settings
import time
from django.http import HttpResponseBadRequest
from googleapiclient.discovery import build

client = Groq(api_key=settings.GROQ_API_KEY)

youtube = build('youtube', 'v3', developerKey=settings.YOUTUBE_API_KEY)\

def home(request):
    return render(request, 'home.html')

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

@login_required
def ask_question(request):
    # Fetch values from the session
    selected_level = request.session.get('selected_level', 'Unknown Level')
    grade_name = request.session.get('grade_name', 'Unknown Grade')
    subject_name = request.session.get('subject_name', 'Unknown Subject')
    
    grade_id = request.session.get('grade_id', 'Unknown Grade')
    subject_id = request.session.get('subject_id', 'Unknown Subject')

    answer = ""
    question = ""
    video_url = ""

    if request.method == "POST":
        question = request.POST.get("question")
        
        if question:
            context = (
                f"You are an assistant for a school system. "
                f"The current school level is '{selected_level}', "
                f"the grade is '{grade_id}', and the subject is '{subject_id}'. "
                f"Provide a detailed, step-by-step guide on how to solve the following question: {question}. "
                f"You can also include any relevant information."
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

            # Removed the validity check for the answer
            # Simply allow any generated answer to be returned

            # Fetch the video URL based on the question
            video_query = f"{question}"
            video_url = fetch_youtube_video(video_query)
            video_url = video_url.replace('watch?v=', 'embed/')
        else:
            answer = "No question was submitted."
    
    return render(request, 'ask_question.html', {'question': question, 'answer': answer, 'video_url': video_url})

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

    if request.method == "POST":
        selected_topic = request.POST.get("topic")  # Focus only on the selected topic

        if selected_topic:  # Ensure that a topic is provided
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

            # Fetch the video URL based on the topic
            video_query = selected_topic
            video_url = fetch_youtube_video(video_query)
            video_url = video_url.replace('watch?v=', 'embed/')
        else:
            answer = "No topic was submitted."
    
    return render(request, 'generate_content.html', {'answer': answer, 'video_url': video_url})



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
