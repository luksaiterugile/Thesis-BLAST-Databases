"""my_project URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from django.conf.urls import include

from django.conf.urls import (
handler400, handler403, handler404, handler500
)


from blast_db_creator import views

# All URL patterns for the project
urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.index, name ='home'),
    path('register/', views.registerpage, name='register'),
    path('login/', views.loginpage, name='login'),
    path('logout/', views.logoutpage, name='logout'),
    path('create_blast_database/', views.create_db_public, 
        name='createpublicdb'),
    path('create-blast-database/', views.create_db_user, 
        name='createuserdb'),
    path('blast_databases/', views.view_db, name='viewdb'),
    path('my-blast-databases/', views.private_blastdb, name='privatedb'),
    path('blastn/<slug:slug>', views.blastn_page, name='blastn'),
    path('blast-results/', 
        views.blast_result_public, 
        name='blastresultpublic'),
    path('blast_results/', views.blast_result_user, name='blastresultuser'),
    path('view-task-result/<slug:slug>', 
        views.view_task_result, 
        name='taskresult'),
    path('blastp/<slug:slug>', views.blastp_page, name='blastp'),
    path('usage/', views.usage, name='usage'),
    path('tblastx/<slug:slug>', views.tblastx_page, name='tblastx'),
    path('tblastn/<slug:slug>', views.tblastn_page, name='tblastn'),
    path('blastx/<slug:slug>', views.blastx_page, name='blastx'),
    path('reset_password/', 
        auth_views.PasswordResetView.as_view(
        template_name="blast_db_creator/reset_password.html"),
        name="reset_password"),
    path('reset_password_sent/', 
        auth_views.PasswordResetDoneView.as_view(
        template_name="blast_db_creator/password_reset_sent.html"), 
        name="password_reset_done"),
    path('reset/<uidb64>/<token>/', 
        auth_views.PasswordResetConfirmView.as_view(
        template_name="blast_db_creator/password_reset_form.html"), 
        name="password_reset_confirm"),
    path('reset_password_complete/', 
        auth_views.PasswordResetCompleteView.as_view(
        template_name="blast_db_creator/password_reset_done.html"), 
        name="password_reset_complete"),
    path('update/<slug:slug>', views.update_blast_db, name='update'),
    path('update-alignment/<slug:slug>', views.update_alignment, 
        name='updatealign'),
    path('generate_tree/<slug:slug>', 
        views.family_tree, name='generatetree'),
    path('retrieve_and_generate_tree/', 
        views.retrieve_and_generate_tree, name='sendslugfield'),
    path('batch-alignment/<slug:slug>', 
        views.batch_alignment, name='multipledb'),
    path('retrieve_multi_dbs_data/', 
        views.retrieve_multi_dbs_data, name='retrieve-multi'),
    path('tasks-list/', views.task_list, name='task_list'),
    path('view_task_outcome/<slug:slug>', 
        views.viewing_task_outcome, name='viewing-task-outcome'),
    path('update_tasks/', views.update_task_list, name='update_task_list'),
    path('404/', views.custom_404, name='custom_404'),
]


urlpatterns += static(settings.MEDIA_URL, 
    document_root=settings.MEDIA_ROOT)
urlpatterns +=  static(settings.STATIC_URL,
        document_root=settings.STATIC_ROOT)

handler404 = 'blast_db_creator.views.custom_404'