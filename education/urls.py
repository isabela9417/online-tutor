from django.urls import path
from . import views
from django.contrib.auth.views import LogoutView

urlpatterns = [
    path('', views.home, name='home'),
    path('login/', views.login_view, name='login'),
    path('signup/', views.signup_view, name='signup'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('select_grade/', views.select_grade, name='select_grade'),
    path('select_subject/', views.select_subject, name='select_subject'),
    path('ask_question/', views.ask_question, name='ask_question'),
    path('rate_performance/', views.rate_performance, name='rate_performance'),
    path('select_school_level/', views.select_school_level, name='select_school_level'),
    path('generate_content/', views.generate_content, name='generate_content'),
    path('voice_assistant/', views.voice_assistant, name='voice_assistant'),
    path('quiz/', views.generate_quiz, name='quiz'), 
    path('submit_quiz/', views.submit_quiz, name='submit_quiz'),
    path('results/<int:score>/<int:total>/<str:passed>/', views.results, name='results'),
    path('generate_quiz/', views.generate_quiz, name='generate_quiz'),
    
]
