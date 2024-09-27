from django.contrib import admin
from .models import Grade, Subject, Question, Quiz, Performance, Question, Document

@admin.register(Grade)
class GradeAdmin(admin.ModelAdmin):
    list_display = ('name', 'level')  
    search_fields = ('name', 'level')  

@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'grade')  
    search_fields = ('name', 'grade__name')  
    list_filter = ('grade',)  
