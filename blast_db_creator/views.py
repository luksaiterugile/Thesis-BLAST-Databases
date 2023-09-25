from pickle import FALSE, TRUE
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from .forms import CreateBlastDBFormPublic, CreateBlastDBFormUser
from .forms import BlastnForm, BlastpForm
from .forms import CreateUserForm, LoginUserForm
from .forms import tBlastnForm, tBlastxForm, BlastxForm
from .models import UserInput, BlastDBData, BlastnUserInput, BlastpUserInput
from .models import BlastnResults, BlastpResults
from .models import UpdateBlastDB
from .models import BlastxUserInput, tBlastnUserInput, tBlastxUserInput
from .models import tBlastnResults, tBlastxResults, BlastxResults
from .models import BatchAlign
from .forms import UpdateBlastDBForm
from django.http import Http404
from django.contrib import messages
from zipfile import ZipFile
from django.http import JsonResponse
from django.urls import reverse
from celery import chain, group, result
import ast
from django.template.loader import render_to_string

import subprocess
import os
import re
import string
import random
import json

from celery.result import GroupResult
from .utils import *
from celery.result import AsyncResult
from django_celery_results.models import TaskResult
from .tasks import *
from celery import Celery
from celery.app.control import Control
import redis
import logging

logger = logging.getLogger("django")


def custom_404(request, exception):
    return render(request, "blast_db_creator/404.html", status=404)


def index(request):
    # Home page view function
    return render(request, "blast_db_creator/index.html")


def registerpage(request):
    # register page view function
    if request.method == 'POST':
        form = CreateUserForm(request.POST)
        if form.is_valid():
            form.save()
            username = form.cleaned_data.get('username')
            messages.success(request, 'Account ' + username + ' was created \
                successfully')
            logger.info(
                f"Account \"{username}\" was created successfully."
            )
            return redirect('login')
        else:
            context = {
                'form': form
            }
            return render(request, "blast_db_creator/register.html", context)
    else:
        # clearing form if request is GET
        form = CreateUserForm()

    context = {
        'form': form
    }
    return render(request, "blast_db_creator/register.html", context)


def loginpage(request):
    # login page view function
    if request.method == 'POST':
        form = LoginUserForm(request, request.POST)
        if form.is_valid():
            username = request.POST.get('username')
            password = request.POST.get('password')
            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                logger.info(
                    f"User \"{username}\" logged in successfully."
                )
                return redirect('home')
            else:
                messages.error(request, "Invalid username or password")
        else:
            messages.error(request, "Invalid username or password")
            context = {
                'form': form,
            }
            return render(request, "blast_db_creator/login.html", context)


    form = LoginUserForm()
    context = {
        'form': form,
    }
    return render(request, "blast_db_creator/login.html", context)


def logoutpage(request):
    # Logging out functionality
    logout(request)
    logger.info(
        f"User logged out successfully."
    )
    return redirect('home')


def retrieve_tasks_info(username):
    # Retrieve currently running tasks
    running_tasks_info = []

    app = Celery('blast_db_creator', 
        broker='redis://localhost:6379', 
        backend='django-db')
    active_tasks = app.control.inspect().active()
    
    logger.info(
        f"Active task retrieval was successful."
    )
    
    # Regex for task names
    pattern_running = r'Running \S+ program$'
    pattern_running_update = \
        r'Running \S+ program for alignments update'
    pattern_generating = r"Generating batch (.*?) alignments"

    if username:
        if active_tasks:
            tasks = [task for worker_tasks in active_tasks.values() 
                for task in worker_tasks]
            # Filling up information to send to view
            if tasks:
                for task in tasks:
                    running_task_information = {}
                    if task['args']:
                        if(username == task['args'][-1]):
                            running_task_information['task_name'] = task['name']
                        arguments = task['args']
                        # Based on task name retrieve item name
                        if task['name'] == "Creating a BLAST database":
                            running_task_information[
                                'item_name'] = task['args'][0]
                        elif task['name'] == "Updating BLAST database":
                            running_task_information[
                                'item_name'] = task['args'][1]
                        elif re.search(pattern_running, task['name']):
                            running_task_information[
                                'item_name'] = task['args'][1]
                        elif re.search(pattern_running_update, task['name']):
                            running_task_information[
                                'item_name'] = task['args'][0]
                        elif re.search(pattern_generating, task['name']):
                            if task['args']:
                                arguments_list = task['args'][0]
                        
                                # Finding common filename
                                pattern = r'^(.+?)-[a-zA-Z0-9]{2}$'

                                common_filename = []
                                for item in arguments_list:
                                    match = re.match(pattern, item)
                                    if match:
                                        common_filename.append(match.group(1))

                                if common_filename:
                                    running_task_information[
                                    'item_name'] = common_filename[0]
                                else:
                                    running_task_information[
                                    'item_name'] = "Batch"


                    elif task['kwargs']:
                        # Some tasks have kwargs instead of args so 
                        # processing these tasks to send to running task table
                        if(username == task['kwargs']['user_id']):
                            running_task_information['task_name'] = task['name']

                            if(task['name'] == "Updating BLAST database"):
                                running_task_information[
                                    'item_name'] = task['kwargs']['father_db']
                            else:
                                if task['kwargs']['alignments']:
                                    alignments_list = task['kwargs'] \
                                        ['alignments']
                                    if alignments_list:
                                        # Finding common filename
                                        pattern = r'^(.+?)-[a-zA-Z0-9]{2}$'

                                        common_filename = []
                                        for item in alignments_list:
                                            match = re.match(pattern, item)
                                            if match:
                                                common_filename.append(
                                                    match.group(1)
                                                )

                                        if common_filename:
                                            running_task_information[
                                            'item_name'] = common_filename[0]
                                        else:
                                            running_task_information[
                                            'item_name'] = "Updating alignments"

                    
                    # Appending to list of dicts
                    running_tasks_info.append(running_task_information)
                    run_tasks_info = [dict(t) for t in {tuple(d.items()) for d in running_tasks_info}]
                    running_tasks_info = run_tasks_info

    if username:
        # Retrieve user tasks
        user_tasks = TaskResult.objects \
            .filter(task_args__icontains=username)

        user_group_tasks = TaskResult.objects \
            .filter(task_kwargs__icontains=username)

        # Split user_group_tasks between BLAST database update and
        # alignment update
        user_group_tasks_dbs = []
        user_group_tasks_alignments = []
        for task in user_group_tasks:
            if task.task_name == "celery.group":
                user_group_tasks_alignments.append(task)

            if task.task_name == "Updating BLAST database":
                user_group_tasks_dbs.append(task)

        logger.info(
            f"Finished task retrieval was successful."
        )

        # Retrieve fields for each task to show in template
        task_results_information = []

        for task in user_tasks:
            # Store information about each task 
            task_dict = {}

            task_dict['task_id'] = task.task_id
            task_dict['task_name'] = task.task_name 
            task_name = task.task_name 
            task_args = task.task_args # Arguments parsed to task
            
            task_dict['status'] = task.status # Task status
            task_dict['date_created'] = task.date_created # Date created
            task_dict['date_done']  = task.date_done # Date finished
            result = task.result # Task result --- 

            pattern_running = r'Running \S+ program$'
            pattern_running_update = \
                r'Running \S+ program for alignments update'

            pattern_generating = r"Generating batch (.*?) alignments"

            # Analyzing item name
            if task_name == "Creating a BLAST database":
                # Retrieve arguments as a list
                pattern = r"'([\w\s@.+_-]+)',\s*'([\w\s@.+_-]+)'"
                
                # Remove leading or trailing whitespace
                task_args_list = tuple(
                    s.strip() for s in re.findall(pattern, task_args)[0])

                task_args = task_args_list
                if task_args:
                    task_args = task_args[0]
                else:
                    task_args = "None"

            elif re.search(pattern_running, task_name):
                # Use regular expressions to retrieve item name
                pattern = r"([\w\-@+._]+)"
                matches = re.findall(pattern, task_args)
                if matches:
                    task_args = matches[1]
                else:
                    task_args = "None"

            elif (re.search(pattern_running_update, task_name)
                or task_name == "Updating BLAST database"):
                # Use regular expressions to retrieve item name
                pattern = r"'(.*?)'"
                matches = re.findall(pattern, task_args)
                if matches:
                    task_args = matches[0]
                else:
                    task_args = "None"

            elif re.search(pattern_generating, task_name):
                pattern = r"'(.*?)'"
                # Inserting items to list
                matches = re.findall(pattern, task_args)

                # Finding the filename that user originally inserted
                pattern = r'^(.+?)-[a-zA-Z0-9]{2}$'

                common_filename = []
                for item in matches:
                    match = re.match(pattern, item)
                    if match:
                        common_filename.append(match.group(1))

                if common_filename:
                    task_args = common_filename[0]
                else:
                    task_args = "None"

            task_dict['item_name'] = task_args
                  
            task_results_information.append(task_dict)

        # Analyze group tasks SUCCESS 
        for group_task in user_group_tasks:
            # Store information about each task 
            task_dict = {}

            task_dict['task_id'] = group_task.task_id
            
            if(group_task.task_name == "celery.group"):
                task_dict['task_name'] = "Updating alignments"
            else:
                task_dict['task_name'] = group_task.task_name

            task_dict['status'] = group_task.status

            task_dict['date_created'] = group_task.date_created

            task_dict['date_done'] = group_task.date_done

            if group_task.status == "SUCCESS":
                task_kwargs = group_task.task_kwargs # Arguments parsed to task
                
                # Converting to suitable data type
                args = json.loads(task_kwargs)
                if isinstance(args, str):
                    args = args.replace("'", '"')
                    args = json.loads(args)

                pattern_alignments = r"Updating\s+\w+\s+alignments$"

                if group_task.task_name == "Updating BLAST database":
                    if args['name']:
                        task_dict['item_name'] = args['father_db']
                    else:
                        task_dict['item_name'] = "None"

                elif re.search(pattern_alignments, group_task.task_name):
                    if args['name']:
                        task_dict['item_name'] = "Updating father's " + \
                        "alignments using " + args['name']
                    else:
                        task_dict['item_name'] = "Updating alignments"

                # Saving results
                task_results_information.append(task_dict)


        # Analyze group tasks db update FAILURE
        failed_dbs_to_update = []
        for updated_db in user_group_tasks_dbs:
            task_dict = {}
            if updated_db.status == "FAILURE":
                task_kwargs = updated_db.task_kwargs # Arguments parsed to task

                # Retrieve arguments as dictionary
                args = json.loads(task_kwargs)
                if isinstance(args, str):
                    args = args.replace("'", '"')
                    args = json.loads(args)
                
                # Filling up data about task
                task_dict['task_id'] = updated_db.task_id
                task_dict['task_name'] = updated_db.task_name
                task_dict['status'] = updated_db.status
                task_dict['date_created'] = updated_db.date_created
                task_dict['date_done'] = updated_db.date_done

                if updated_db.task_name == "Updating BLAST database":
                    if args['name']:
                        task_dict['item_name'] = args['father_db']
                        failed_dbs_to_update.append(args['name'])
                    else:
                        task_dict['item_name'] = "None"
            
                # Saving results
                task_results_information.append(task_dict)

        # Analyze group alignment tasks SUCCESS/FAILURE
        for updating_align in user_group_tasks_alignments:
            task_dict = {}
            task_kwargs = updating_align.task_kwargs # Arguments parsed to task

            # Retrieve arguments as dictionary
            args = json.loads(task_kwargs)
            if isinstance(args, str):
                args = args.replace("'", '"')
                args = json.loads(args)

            if updating_align.status == "FAILURE":
                # Check if the alignment was failure or db update was failure
                if updating_align.task_name == "celery.group":
                    updating_using = [task['kwargs']['name'] \
                        for task in args['tasks']]

                    if updating_using:
                        if updating_using[0] in failed_dbs_to_update:
                            # Alignments updated failed because BLAST
                            # DB update failed
                            task_dict['item_name'] = \
                                F"Updating father's alignments using" \
                                F" \"{updating_using[0]}\" " 
                        else:
                            # Some or all alignments update failed, BLAST
                            # DB update successful
                            task_dict['item_name'] = \
                                F"Updating father's alignments using" \
                                F" \"{updating_using[0]}\" " 

                        # Filling up data about task
                        task_dict['task_id'] = updating_align.task_id
                        task_dict['task_name'] = "Updating alignments"
                        task_dict['status'] = updating_align.status
                        task_dict['date_created'] = updating_align.date_created
                        task_dict['date_done'] = updating_align.date_done
 
                        # Saving results
                        task_results_information.append(task_dict)

    return running_tasks_info, task_results_information


@login_required(login_url='login')
def task_list(request):
    # Delete selected tasks from AJAX method
    if request.method == 'POST':
        task_ids = request.POST.getlist('task_names[]')
        if(task_ids):
            for task_id in task_ids:
                if(TaskResult.objects.filter(task_id=task_id).exists()):
                    task_obj = TaskResult.objects \
                        .filter(task_id=task_id).first()
                    task_obj.delete()
            logger.info(
                f"Selected finished tasks were removed successfully."
            )
        else:
            logger.warning(
                f"Selected finished tasks were removed unsuccessfully."
            )

    running_tasks_info, task_results_information = retrieve_tasks_info(
        request.user.username)
    
    context = {
        'tasks': task_results_information,
        'running_tasks': running_tasks_info
    }
    return render(request, "blast_db_creator/tasks.html", context)


def update_task_list(request):
    if request.user.is_authenticated:
        running_tasks_info, task_results_information = retrieve_tasks_info(
            request.user.username)

        data = {
            'tasks': task_results_information, 
            'running_tasks': running_tasks_info
        }
        return JsonResponse(data)



def viewing_task_outcome(request, slug=None):
    # Retrieve TaskResult object
    task = TaskResult.objects.filter(task_id=slug).first()

    app = Celery('blast_db_creator', 
        broker='redis://localhost:6379', 
        backend='django-db')

    logger.info(
        f"Redirecting user based on task status and task name."
    )

    # Pattern for retrieving specific alignment name
    pattern_alignments = r"Updating\s+\w+\s+alignments$"

    if task.task_name == "Creating a BLAST database":
        if task.status == "SUCCESS":
            # Retrieve database to know if its public or private
            pattern = r"'([\w\s@.+_-]+)',\s*'([\w\s@.+_-]+)'"
                
            # Remove leading or trailing whitespace
            task_args_list = tuple(
                s.strip() for s in re.findall(pattern, task.task_args)[0])

            if(UserInput.objects \
                .filter(name_of_blast_db=task_args_list[0]).exists()):
                db_user_input = UserInput.objects \
                .filter(name_of_blast_db=task_args_list[0]).first()

                # Redirecting user 
                if db_user_input.public_or_private == "public":
                    return redirect('viewdb')
                elif db_user_input.public_or_private == "private":
                    return redirect('privatedb')

        elif task.status == "FAILURE":
            task_result = AsyncResult(task.task_id)
            messages.error(request, str(task_result.result))
            return redirect('createuserdb')
 
    elif(task.task_name == "Running BLASTn program" 
        or task.task_name == "Running BLASTn program for alignments update"):
        # Redirecting user depending on the status of task
        if task.status == "SUCCESS":
            matches = re.findall(r"([\w\-@+._]+)", task.task_args)
            if matches:
                obj_name = matches[1]
                if(BlastnUserInput.objects
                    .filter(output_filename=str(obj_name)).exists()):
                    obj_blastn = BlastnUserInput.objects \
                        .filter(output_filename=str(obj_name)).first()
                    if(obj_blastn):
                        if(obj_blastn.database.user_input.public_or_private == "public"):
                            return redirect('blastresultpublic')
                        elif(obj_blastn.database.user_input.public_or_private == "private"):
                            return redirect('blastresultuser')
                    return redirect('blastresultuser')
            else:
                return redirect('blastresultuser')
            
        elif task.status == "FAILURE":
            pattern = r"([\w\-@+._]+)"
            matches = re.findall(pattern, task.task_args)
            if matches:
                task_result = AsyncResult(task.task_id)
                messages.error(request, str(task_result.result))
                return redirect('blastn', str(matches[0]))

    elif(task.task_name == "Running BLASTp program" 
        or task.task_name == "Running BLASTp program for alignments update"):
        # Redirecting user depending on the status of task
        if task.status == "SUCCESS":
            matches = re.findall(r"([\w\-@+._]+)", task.task_args)
            if matches:
                obj_name = matches[1]
                if(BlastpUserInput.objects
                    .filter(output_filename=str(obj_name)).exists()):
                    obj_blastp = BlastpUserInput.objects \
                        .filter(output_filename=str(obj_name)).first()
                    if(obj_blastp):
                        if(obj_blastp.database.user_input.public_or_private == "public"):
                            return redirect('blastresultpublic')
                        elif(obj_blastp.database.user_input.public_or_private == "private"):
                            return redirect('blastresultuser')
                    return redirect('blastresultuser')
            else:
                return redirect('blastresultuser')

        elif task.status == "FAILURE":
            pattern = r"([\w\-@+._]+)"
            matches = re.findall(pattern, task.task_args)
            if matches:
                task_result = AsyncResult(task.task_id)
                messages.error(request, str(task_result.result))
                return redirect('blastp', str(matches[0]))
    
    elif(task.task_name == "Running BLASTx program" 
        or task.task_name == "Running BLASTx program for alignments update"):
        # Redirecting user depending on the status of task
        if task.status == "SUCCESS":
            matches = re.findall(r"([\w\-@+._]+)", task.task_args)
            if matches:
                obj_name = matches[1]
                if(BlastxUserInput.objects
                    .filter(output_filename=str(obj_name)).exists()):
                    obj_blastx = BlastxUserInput.objects \
                        .filter(output_filename=str(obj_name)).first()
                    if(obj_blastx):
                        if(obj_blastx.database.user_input.public_or_private == "public"):
                            return redirect('blastresultpublic')
                        elif(obj_blastx.database.user_input.public_or_private == "private"):
                            return redirect('blastresultuser')
                    return redirect('blastresultuser')
            else:
                return redirect('blastresultuser')

        elif task.status == "FAILURE":
            pattern = r"([\w\-@+._]+)"
            matches = re.findall(pattern, task.task_args)
            if matches:
                task_result = AsyncResult(task.task_id)
                messages.error(request, str(task_result.result))
                return redirect('blastx', str(matches[0]))

    elif(task.task_name == "Running tBLASTn program" 
        or task.task_name == "Running tBLASTn program for alignments update"):
        # Redirecting user depending on the status of task
        if task.status == "SUCCESS":
            matches = re.findall(r"([\w\-@+._]+)", task.task_args)
            if matches:
                obj_name = matches[1]
                if(tBlastnUserInput.objects
                    .filter(output_filename=str(obj_name)).exists()):
                    obj_tblastn = tBlastnUserInput.objects \
                        .filter(output_filename=str(obj_name)).first()
                    if(obj_tblastn):
                        if(obj_tblastn.database.user_input.public_or_private == "public"):
                            return redirect('blastresultpublic')
                        elif(obj_tblastn.database.user_input.public_or_private == "private"):
                            return redirect('blastresultuser')
                    return redirect('blastresultuser')
            else:
                return redirect('blastresultuser')

        elif task.status == "FAILURE":
            pattern = r"([\w\-@+._]+)"
            matches = re.findall(pattern, task.task_args)
            if matches:
                task_result = AsyncResult(task.task_id)
                messages.error(request, str(task_result.result))
                return redirect('tblastn', str(matches[0]))

    elif(task.task_name == "Running tBLASTx program" 
        or task.task_name == "Running tBLASTx program for alignments update"):
        # Redirecting user depending on the status of task
        if task.status == "SUCCESS":
            matches = re.findall(r"([\w\-@+._]+)", task.task_args)
            if matches:
                obj_name = matches[1]
                if(tBlastxUserInput.objects
                    .filter(output_filename=str(obj_name)).exists()):
                    obj_tblastx = tBlastxUserInput.objects \
                        .filter(output_filename=str(obj_name)).first()
                    if(obj_tblastx):
                        if(obj_tblastx.database.user_input.public_or_private == "public"):
                            return redirect('blastresultpublic')
                        elif(obj_tblastx.database.user_input.public_or_private == "private"):
                            return redirect('blastresultuser')
                    return redirect('blastresultuser')
            else:
                return redirect('blastresultuser')

        elif task.status == "FAILURE":
            pattern = r"([\w\-@+._]+)"
            matches = re.findall(pattern, task.task_args)
            if matches:
                task_result = AsyncResult(task.task_id)
                messages.error(request, str(task_result.result))
                return redirect('tblastx', str(matches[0]))

    elif(task.task_name == "Generating batch BLASTn alignments"):
        result = AsyncResult(task.task_id)

        if task.status == "SUCCESS":
            # Inserting items to list
            alignments = re.findall(r"'([a-zA-Z0-9_@+.-]+)'", task.task_args)
            alignments = alignments[:-1]
            batch_id = alignments[-1]

            if(result.info):
                result_dict = result.info
                if('info' in result_dict):
                    info_dict = result_dict['info']
                    if(info_dict):
                        messages.warning(request, (
                            F"Some alignments: "
                            F" \"{', '.join(info_dict.keys())}\" "
                            F"couldn't be generated. One of the "
                            F"errors that BLASTn "
                            F" presented is: "
                            F"{str(next(iter(info_dict.values())))}"
                            F". Please check for any mistakes that" 
                            F" you have made."
                            F" Other alignments that are not in"
                            F" the list generated "
                            F"succesfully."
                        ))

            return redirect('multipledb', batch_id)

        elif task.status == "FAILURE":
            # All failed (Exception) 
            if(result.result):
                # Exception will be dict
                if isinstance(result.result.args[0], dict):
                    blastn_errors_alignments = result.result.args[0]
                    messages.error(request, (
                        F"Couldn't generate any alignments for selected "
                        F"BLAST databases. The error from BLASTn program: "
                        F"{str(next(iter(blastn_errors_alignments.values())))} "
                        F"Please check the mistakes and try running "
                        F"batch alignment generation for many BLAST databases "
                        F"again."
                    ))
                    return redirect('privatedb')

    elif(task.task_name == "Generating batch BLASTp alignments"):
        result = AsyncResult(task.task_id)

        if task.status == "SUCCESS":
            alignments = re.findall(r"'([a-zA-Z0-9_@+.-]+)'", task.task_args)
            alignments = alignments[:-1]
            batch_id = alignments[-1]

            if(result.info):
                result_dict = result.info
                if('info' in result_dict):
                    info_dict = result_dict['info']
                    if(info_dict):
                        messages.warning(request, (
                            F"Some alignments: "
                            F" \"{', '.join(info_dict.keys())}\" "
                            F"couldn't be generated. One of the "
                            F"errors that BLASTp "
                            F" presented is: "
                            F"{str(next(iter(info_dict.values())))}"
                            F". Please check for any mistakes that" 
                            F" you have made."
                            F" Other alignments that are not in"
                            F" the list generated "
                            F"succesfully."
                        ))
            return redirect('multipledb', batch_id)

        elif task.status == "FAILURE":
            # All failed (Exception) 
            if(result.result):
                # Exception will be dict
                if isinstance(result.result.args[0], dict):
                    blastp_errors_alignments = result.result.args[0]
                    messages.error(request, (
                        F"Couldn't generate any alignments for selected "
                        F"BLAST databases. The error from BLASTp program: "
                        F"{str(next(iter(blastp_errors_alignments.values())))}"
                        F". Please check the mistakes and try running "
                        F"batch alignment generation for many BLAST databases "
                        F"again."
                    ))
                    return redirect('privatedb')


    elif(task.task_name == "Generating batch BLASTx alignments"):
        result = AsyncResult(task.task_id)

        if task.status == "SUCCESS":
            alignments = re.findall(r"'([a-zA-Z0-9_@+.-]+)'", task.task_args)
            alignments = alignments[:-1]
            batch_id = alignments[-1]

            if(result.info):
                result_dict = result.info
                if('info' in result_dict):
                    info_dict = result_dict['info']
                    if(info_dict):
                        messages.warning(request, (
                            F"Some alignments: "
                            F" \"{', '.join(info_dict.keys())}\" "
                            F"couldn't be generated. One of the "
                            F"errors that BLASTx "
                            F" presented is: "
                            F"{str(next(iter(info_dict.values())))}"
                            F". Please check for any mistakes that" 
                            F" you have made."
                            F" Other alignments that are not in"
                            F" the list generated "
                            F"succesfully."
                        ))
            return redirect('multipledb', batch_id)

        elif task.status == "FAILURE":
            # All failed (Exception) 
            if(result.result):
                # Exception will be dict
                if isinstance(result.result.args[0], dict):
                    blastx_errors_alignments = result.result.args[0]
                    messages.error(request, (
                        F"Couldn't generate any alignments for selected "
                        F"BLAST databases. The error from BLASTx program: "
                        F"{str(next(iter(blastx_errors_alignments.values())))}"
                        F". Please check the mistakes and try running "
                        F"batch alignment generation for many BLAST databases "
                        F"again."
                    ))
                    return redirect('privatedb')

    elif(task.task_name == "Generating batch tBLASTn alignments"):
        result = AsyncResult(task.task_id)

        if task.status == "SUCCESS":
            alignments = re.findall(r"'([a-zA-Z0-9_@+.-]+)'", task.task_args)
            alignments = alignments[:-1]
            batch_id = alignments[-1]

            if(result.info):
                result_dict = result.info
                if('info' in result_dict):
                    info_dict = result_dict['info']
                    if(info_dict):
                        messages.warning(request, (
                            F"Some alignments: "
                            F" \"{', '.join(info_dict.keys())}\" "
                            F"couldn't be generated. One of the "
                            F"errors that tBLASTn "
                            F" presented is: "
                            F"{str(next(iter(info_dict.values())))}"
                            F". Please check for any mistakes that" 
                            F" you have made."
                            F" Other alignments that are not in"
                            F" the list generated "
                            F"succesfully."
                        ))
            return redirect('multipledb', batch_id)

        elif task.status == "FAILURE":
            # All failed (Exception) 
            if(result.result):
                # Exception will be dict
                if isinstance(result.result.args[0], dict):
                    tblastn_errors_alignments = result.result.args[0]
                    messages.error(request, (
                        F"Couldn't generate any alignments for selected "
                        F"BLAST databases. The error from tBLASTn program: "
                        F"{str(next(iter(tblastn_errors_alignments.values())))}"
                        F". Please check the mistakes and try running "
                        F"batch alignment generation for many BLAST databases "
                        F"again."
                    ))
                    return redirect('privatedb')

    elif(task.task_name == "Generating batch tBLASTx alignments"):
        result = AsyncResult(task.task_id)

        if task.status == "SUCCESS":
            alignments = re.findall(r"'([a-zA-Z0-9_@+.-]+)'", task.task_args)
            alignments = alignments[:-1]
            batch_id = alignments[-1]

            if(result.info):
                result_dict = result.info
                if('info' in result_dict):
                    info_dict = result_dict['info']
                    if(info_dict):
                        messages.warning(request, (
                            F"Some alignments: "
                            F" \"{', '.join(info_dict.keys())}\" "
                            F"couldn't be generated. One of the "
                            F"errors that tBLASTx "
                            F" presented is: "
                            F"{str(next(iter(info_dict.values())))}"
                            F". Please check for any mistakes that" 
                            F" you have made."
                            F" Other alignments that are not in"
                            F" the list generated "
                            F"succesfully."
                        ))
            return redirect('multipledb', batch_id)

        elif task.status == "FAILURE":
            # All failed (Exception) 
            if(result.result):
                # Exception will be dict
                if isinstance(result.result.args[0], dict):
                    tblastx_errors_alignments = result.result.args[0]
                    messages.error(request, (
                        F"Couldn't generate any alignments for selected "
                        F"BLAST databases. The error from tBLASTx program: "
                        F"{str(next(iter(tblastx_errors_alignments.values())))}"
                        F". Please check the mistakes and try running "
                        F"batch alignment generation for many BLAST databases "
                        F"again."
                    ))
                    return redirect('privatedb')
    

    elif(task.task_name == "Updating BLAST database"):
        if task.status == "SUCCESS":
            return redirect('privatedb')
        elif task.status == "FAILURE":
            if('exc_message' in task.result):
                result = task.result
                result = json.loads(task.result)
                if isinstance(result, str):
                    result = args.replace("'", '"')
                    result = json.loads(args)

                if(result):
                    messages.error(request, 
                        F"Couldn't update the BLAST database. "
                        F"The error from processing: "
                        F"{str(result['exc_message'][0])}."
                        F"Please check the mistakes and try running "
                        F"BLAST database"
                        F" update again."
                    )
                    return redirect('privatedb')

    elif(re.search(pattern_alignments, task.task_name)):
        # Updating alignments from Updating BLAST database
        if task.status == "SUCCESS":
            return redirect('blastresultuser')
        

    elif(task.task_name == "celery.group"):
        if task.status == "FAILURE":
            # Either all group failed or only some
            task_result = AsyncResult(task.task_id)
            arguments = json.loads(task.task_kwargs)
            group_tasks = arguments['tasks']

            # Save task id, name and status 
            tasks_in_group = {}
            for task in group_tasks:
                # Check if any of them are succesful 
                task_id = task['options']['task_id']
                if(TaskResult.objects.filter(task_id=task_id).exists()):
                    task_result = TasksResult.objects \
                        .filter(task_id=task_id).first()
                    tasks_in_group[task_id] = [task['task'], task_result.status]
                else:
                    tasks_in_group[task_id] = [task['task'], "None"]
                
            # Check if all not initialized or failed
            statuses = [value[1] for value in tasks_in_group.values()]
            if all(value == "None" for value in statuses):
                messages.error(request, (
                    F"Could not update any alignments, because BLAST "
                    F"database was not created succesfully. Please try again"
                    F" and ensure that all the data provided is correct."
                ))
            elif all(value == "FAILED" for value in statuses):
                messages.warning(request, (
                    F"Could not update any alignments. You can also update"
                    F" needed alignments separately in alignments page. "
                ))
            elif all(value != "None" for value in statuses):
                successful_tasks = []
                failed_tasks = []
                for task_id, task_info in tasks_in_group.items():
                    task_name = task_info[0]
                    task_status = task_info[1]
                    if task_status == "SUCCESS":
                        successful_tasks.append(task_name)
                    else:
                        failed_tasks.append(task_name)

                # Only keep the type of program
                if(successful_tasks):
                    for i, task in enumerate(successful_tasks):
                        match = re.match(
                            r'^Updating\s+(tBLASTx|BLASTx|BLASTp|'
                            r'tBLASTn|BLASTn)\s+alignments$', 
                            task)
                        if match:
                            successful_tasks[i] = match.group(1)

                if(failed_tasks):
                    for i, task in enumerate(failed_tasks):
                        match = re.match(
                            r'^Updating\s+(tBLASTx|BLASTx|BLASTp|'
                            r'tBLASTn|BLASTn)\s+alignments$', 
                            task)
                        if match:
                            successful_tasks[i] = match.group(1)

                if(succesful_tasks and failed_tasks):
                    messages.warning(request, (
                        F"Could not update all alignments. "
                        F"Could not update "
                        F"\"{', '.join(failed_tasks)}\" program's alignments."
                        F" But \"{', '.join(succesful_tasks)}\" program's "
                        F"alignments were updated succesfully."
                        F" You could also use alignments page to update "
                        F"specific alignments individually."
                    ))
            return redirect('blastresultuser')
                
    return redirect('task_list')


def create_db_public(request):
    # Creating public BLAST database view function
    if request.method == 'POST':
        form = CreateBlastDBFormPublic(request.POST, request.FILES)
        if form.is_valid():
            if form.instance.public_or_private == 'public':
                form.save()
                logger.info(
                    f"User input saving for BLAST database creation "
                    f"was created successfully."
                )
            error_blast = createdb(form.instance.name_of_blast_db, False)
            if error_blast:
                user_input_obj = UserInput.objects.get(
                    name_of_blast_db=form.instance.name_of_blast_db)
                user_input_obj.delete()
                messages.error(request, str(error_blast))
            else:
                saveblastdb_data(form.instance.name_of_blast_db)
                # redirecting to page if successful
                return redirect('viewdb')
        else:
            context = {
                'form_public': form
            }
            return render(request, 
                "blast_db_creator/create_db_public.html", context)

    else:
        form = CreateBlastDBFormPublic()
    
    context = {
        'form_public': form
    }
 
    return render(request, "blast_db_creator/create_db_public.html", context)


@login_required(login_url='login')
def create_db_user(request):
    if request.method == 'POST':
        form = CreateBlastDBFormUser(request.POST, request.FILES)
        if form.is_valid():
            new_request = form.save(commit=False)
            # Adding additional information about object
            if new_request.public_or_private == 'private':
                db_type = new_request.public_or_private
                if request.user.is_authenticated:
                    new_request.user = request.user
                    new_request.save()
                    logger.info(
                        f"User input for BLAST database creation "
                        f"was saved successfully."
                    )
                else:
                    messages.error(request, "Private databases " +
                                   "available for logged in users only.")
                    return redirect('login')
            elif new_request.public_or_private == 'public':
                db_type = new_request.public_or_private
                new_request.save()
                logger.info(
                    f"User input for BLAST database creation "
                    f"was saved successfully."
                )

            # Initialize task in Celery
            createdb_task.delay(form.instance.name_of_blast_db, 
                request.user.username)
            
            messages.info(request, (
                f"Creating the \"{form.instance.name_of_blast_db}\" "
                f"BLAST database. "
                f"When the processing is finished, the result will appear in "
                f"the table. "
            ))

            # Redirect user to all task list to view the progress
            return redirect('task_list')

        else:
            context = {
                'form_user': form,
            }
            return render(request, 
                "blast_db_creator/create_db_user.html", context)

    else:
        # If request method is GET, form is cleared
        form = CreateBlastDBFormUser()

    context = {
        'form_user': form,
    }
    return render(request, "blast_db_creator/create_db_user.html", context)


    
def view_db(request):
    # Rendering view of all public BLAST databases
    blast_db_data = BlastDBData.objects \
        .filter(user_input__public_or_private="public")

    logger.info(
        f"Retrieval of BLAST databases objects "
        f"was successful."
    )

    context = {
        'blast_db_data': blast_db_data,
    }

    return render(request, "blast_db_creator/view_db.html", context)


def remove_user_files(obj_name):
    db_path = 'media/blast_databases/'
    user_inputs_path = 'media/users_inputs/'
    user_taxid_files_path = 'media/user_taxid_files/'
    user_inputs_update = 'media/blast_db_updates/'

    tblastn_align_out = 'media/tblastn_outputs/'
    tblastx_align_out = 'media/tblastx_outputs/'
    blastx_align_out = 'media/blastx_outputs/'
    blastp_align_out = 'media/blastp_outputs/'
    blastn_align_out = 'media/blastn_outputs/'

    logger.info(
        f"Removing objects and corresponding files."
    )

    if(UserInput.objects.filter(name_of_blast_db=obj_name).exists()):
        # Retrieve user input and result objects from models
        db_user_input = UserInput.objects \
            .filter(name_of_blast_db=obj_name).first()
        db_object = BlastDBData.objects.filter(slug=obj_name).first()
        updated_dbs_files = False

        if(db_user_input and db_object):
            if(db_object.father_database == None):
                # Might be father or just BLAST database by itself
                if(BlastDBData.objects \
                    .filter(father_database=db_object)):

                    # If previously it was child but now its father
                    if(UpdateBlastDB.objects \
                        .filter(database=db_object).exists()):
                        # Retrieving update object
                        update_obj = UpdateBlastDB.objects \
                            .filter(database=db_object).first()
                        uupdated_dbs_files = True
                        # Remove input file
                        remove_inputs(user_inputs_update,
                            str(updated_obj.updated_file_input))
                        remove_inputs(
                            user_inputs_update,
                            str(updated_obj.input_file))
                        # Remvoing update object
                        update_obj.delete()

                    # Removing BLAST DB which is a father DB
                    # 1. Remove only alignment objects because user files are
                    # used in children DBs
                    if(BlastnUserInput.objects \
                        .filter(database=db_object) \
                            .exists()):
                        # Retrieving objects of father
                        blastn_objects = BlastnUserInput.objects \
                            .filter(database=db_object)

                        if(blastn_objects):
                            for obj in blastn_objects:
                                # If query file used, do not delete it
                                if(BlastnUserInput.objects.filter(
                                    query_file=obj.query_file
                                ).exclude(output_filename=obj.output_filename) 
                                .exists()):
                                    remove_inputs(
                                        blastn_align_out, 
                                        obj.output_filename)
                                    obj.delete()
                                else:
                                    remove_blastn_alignment(
                                        str(obj.output_filename)
                                    )
                            
                    if(BlastpUserInput.objects \
                        .filter(database=db_object) \
                            .exists()):
                        # Retrieving objects of father
                        blastp_objects = BlastpUserInput.objects \
                            .filter(database=db_object)

                        if(blastp_objects):
                            for obj in blastp_objects:
                                # If query file used, do not delete it
                                if(BlastpUserInput.objects.filter(
                                    query_file=obj.query_file
                                ).exclude(output_filename=obj.output_filename)
                                .exists()):
                                    remove_inputs(
                                        blastp_align_out, 
                                        obj.output_filename)
                                    obj.delete()
                                else:
                                    remove_blastp_alignment(
                                        str(obj.output_filename)
                                    )

                    if(tBlastxUserInput.objects \
                        .filter(database=db_object) \
                            .exists()):
                        # Retrieving objects
                        tblastx_objects = tBlastxUserInput.objects \
                            .filter(database=db_object)

                        if(tblastx_objects):
                            for obj in tblastx_objects:
                                # If query file used, do not delete it
                                if(tBlastxUserInput.objects.filter(
                                    query_file=obj.query_file
                                ).exclude(output_filename=obj.output_filename)
                                .exists()):
                                    remove_inputs(
                                        tblastx_align_out, 
                                        obj.output_filename)
                                    obj.delete()
                                else:
                                    remove_tblastx_alignment(
                                        str(obj.output_filename)
                                    )
                            
                    if(tBlastnUserInput.objects \
                        .filter(database=db_object) \
                            .exists()):
                        # Retrieving objects
                        tblastn_objects = tBlastnUserInput.objects \
                            .filter(database=db_object)

                        if(tblastn_objects):
                            for obj in tblastn_objects:
                                # If query file used, do not delete it
                                if(tBlastnUserInput.objects.filter(
                                    query_file=obj.query_file
                                ).exclude(output_filename=obj.output_filename)
                                .exists()):
                                    remove_inputs(
                                        tblastn_align_out, 
                                        obj.output_filename)
                                    obj.delete()
                                else:
                                    remove_tblastn_alignment(
                                        str(obj.output_filename)
                                    )
                            
                    if(BlastxUserInput.objects \
                        .filter(database=db_object) \
                            .exists()):
                        # Retrieving objects
                        blastx_obj = BlastxUserInput.objects \
                            .filter(database=db_object)

                        if(blastx_obj):
                            for obj in blastx_obj:
                                # If query file used, do not delete it
                                if(BlastxUserInput.objects.filter(
                                    query_file=obj.query_file
                                ).exclude(output_filename=obj.output_filename)
                                .exists()):
                                    remove_inputs(
                                        blastx_align_out, 
                                        obj.output_filename)
                                    obj.delete()
                                else:
                                    remove_blastx_alignment(
                                        str(obj.output_filename)
                                    )
                           
                    # 2. Removing UserInput object.
                    # BlastDBData will be deleted together with UserInput
                    # Remove zip file 
                    remove_database_data(
                        db_path, 
                        db_user_input.name_of_blast_db)
                    
                    if not (UserInput.objects.filter(
                        input_file=db_user_input.input_file
                    ).exclude(
                        name_of_blast_db=db_user_input.name_of_blast_db
                    ).exists()):
                        if not updated_dbs_files:
                            remove_inputs(
                                user_inputs_path,
                                db_user_input.input_file
                            )
                            remove_inputs(
                                user_taxid_files_path,
                                db_user_input.taxid_map
                            )

                else:
                    # BLAST DB does not have children DBs
                    if(UpdateBlastDB.objects \
                        .filter(database=db_object).exists()):
                        # Retrieving update object
                        update_obj = UpdateBlastDB.objects \
                            .filter(database=db_object).first()
                        updated_dbs_files = True
                        # Removing input file
                        remove_inputs(
                            user_inputs_update, 
                            update_obj.updated_file_input)
                        remove_inputs(
                            user_inputs_update,
                            db_user_input.input_file)

                        # Remvoing update object
                        update_obj.delete()
                    # BLAST database without any relations to other DBs
                    # 1. Removing alignment objects and input files
                    if(BlastnUserInput.objects \
                        .filter(database=db_object) \
                            .exists()):
                        # Retrieving objects
                        blastn_objects = BlastnUserInput.objects \
                            .filter(database=db_object)

                        # Looping through objects
                        if(blastn_objects):
                            for obj in blastn_objects:
                                # Removing files and object
                                remove_blastn_alignment(
                                    str(obj.output_filename))

                    if(BlastpUserInput.objects \
                        .filter(database=db_object) \
                            .exists()):
                        # Retrieving objects
                        blastp_objects = BlastpUserInput.objects \
                            .filter(database=db_object)

                        # Looping through objects
                        if(blastp_objects):
                            for obj in blastp_objects:
                                # Removing files and object
                                remove_blastp_alignment(
                                    str(obj.output_filename))

                    if(tBlastxUserInput.objects \
                        .filter(database=db_object) \
                            .exists()):
                        # Retrieving objects
                        tblastx_objects = tBlastxUserInput.objects \
                            .filter(database=db_object)

                        # Looping through objects
                        if(tblastx_objects):
                            for obj in tblastx_objects:
                                # Removing files and object
                                remove_tblastx_alignment(
                                    str(obj.output_filename))

                    if(tBlastnUserInput.objects \
                        .filter(database=db_object) \
                            .exists()):
                        # Retrieving objects
                        tblastn_objects = tBlastnUserInput.objects \
                            .filter(database=db_object)

                        # Looping through objects
                        if(tblastn_objects):
                            for obj in tblastn_objects:
                                # Removing files and objects
                                remove_tblastn_alignment(
                                    str(obj.output_filename))

                    if(BlastxUserInput.objects \
                        .filter(database=db_object) \
                            .exists()):
                        # Retrieving objects
                        blastx_obj = BlastxUserInput.objects \
                            .filter(database=db_object)

                        # Looping through objects
                        if(blastx_obj):
                            for obj in blastx_obj:
                                # Removing files and objects
                                remove_blastx_alignment(
                                    str(obj.output_filename))


                    # 2. Removing database files and UserInput object
                    # BlastDBData will be deleted together with UserInput
                    # Remove zip file and its files 
                    remove_database_data(
                        db_path, 
                        db_user_input.name_of_blast_db)
                    
                    if not (
                        UserInput.objects.filter(
                            input_file=db_user_input.input_file
                        ).exclude(
                            name_of_blast_db=db_user_input.name_of_blast_db
                        ).exists()):
                        if not updated_dbs_files:
                            # Remove input file
                            remove_inputs(
                                user_inputs_path,
                                db_user_input.input_file
                            )
                            # Remove taxid map file
                            remove_inputs(
                                user_taxid_files_path,
                                db_user_input.taxid_map
                            )

            else:
                # This is child BLAST DB remove UpdateBlastDB
                # Remove database
                # Check if there are any other child databases asociated with
                # selected db - if yes, do not remove files, if no - remove all
                father_db = db_object.father_database
                updated_dbs_files = False
                if(UpdateBlastDB.objects.filter(database=db_object).exists()):
                    # Retrieving update object
                    update_obj = UpdateBlastDB.objects \
                        .filter(database=db_object).first()
                    # Removing input file
                    updated_dbs_files = True
                    remove_inputs(
                        user_inputs_update, 
                        update_obj.updated_file_input)
                    remove_inputs(
                        user_inputs_update,
                        db_user_input.input_file)
                    # Remvoing update object
                    update_obj.delete()
                
                if(BlastDBData.objects \
                    .filter(father_database=father_db).exists()):
                    # Retrieve all fathers children
                    updated_dbs = BlastDBData.objects \
                        .filter(father_database=father_db)
                    if(len(updated_dbs) > 1):
                        # There are still other children asociated with this
                        # father
                        # 1. Remove only alignment objects
                        if(BlastnUserInput.objects \
                        .filter(database=db_object) \
                            .exists()):
                            # Retrieving objects
                            blastn_objects = BlastnUserInput.objects \
                                .filter(database=db_object)

                            if(blastn_objects):
                                for obj in blastn_objects:
                                    if(BlastnUserInput.objects.filter(
                                        query_file=obj.query_file
                                    ).exclude(output_filename=obj.output_filename)
                                    .exists()):
                                        remove_inputs(
                                            blastn_align_out, 
                                            obj.output_filename)
                                        obj.delete()
                                    else:
                                        remove_blastn_alignment(
                                            str(obj.output_filename)
                                        )

                        if(BlastpUserInput.objects \
                            .filter(database=db_object) \
                                .exists()):
                            # Retrieving objects
                            blastp_objects = BlastpUserInput.objects \
                                .filter(database=db_object)

                            if(blastp_objects):
                                for obj in blastp_objects:
                                    # If query file used, do not delete it
                                    if(BlastpUserInput.objects.filter(
                                        query_file=obj.query_file
                                    ).exclude(output_filename=obj.output_filename)
                                    .exists()):
                                        remove_inputs(
                                            blastp_align_out, 
                                            obj.output_filename)
                                        obj.delete()
                                    else:
                                        remove_blastp_alignment(
                                            str(obj.output_filename)
                                        )

                        if(tBlastxUserInput.objects \
                            .filter(database=db_object) \
                                .exists()):
                            # Retrieving objects
                            tblastx_objects = tBlastxUserInput.objects \
                                .filter(database=db_object)

                            if(tblastx_objects):
                                for obj in tblastx_objects:
                                    # If query file used, do not delete it
                                    if(tBlastxUserInput.objects.filter(
                                        query_file=obj.query_file
                                    ).exclude(output_filename=obj.output_filename)
                                    .exists()):
                                        remove_inputs(
                                            tblastx_align_out, 
                                            obj.output_filename)
                                        obj.delete()
                                    else:
                                        remove_tblastx_alignment(
                                            str(obj.output_filename)
                                        )

                        if(tBlastnUserInput.objects \
                            .filter(database=db_object) \
                                .exists()):
                            # Retrieving objects
                            tblastn_objects = tBlastnUserInput.objects \
                                .filter(database=db_object)

                            if(tblastn_objects):
                                for obj in tblastn_objects:
                                    # If query file used, do not delete it
                                    if(tBlastnUserInput.objects.filter(
                                        query_file=obj.query_file
                                    ).exclude(output_filename=obj.output_filename)
                                    .exists()):
                                        remove_inputs(
                                            tblastn_align_out, 
                                            obj.output_filename)
                                        obj.delete()
                                    else:
                                        remove_tblastn_alignment(
                                            str(obj.output_filename)
                                        )

                        if(BlastxUserInput.objects \
                            .filter(database=db_object) \
                                .exists()):
                            # Retrieving objects
                            blastx_obj = BlastxUserInput.objects \
                                .filter(database=db_object)

                            if(blastx_obj):
                                for obj in blastx_obj:
                                    # If query file used, do not delete it
                                    if(BlastxUserInput.objects.filter(
                                        query_file=obj.query_file
                                    ).exclude(output_filename=obj.output_filename)
                                    .exists()):
                                        remove_inputs(
                                            blastx_align_out, 
                                            obj.output_filename)
                                        obj.delete()
                                    else:
                                        remove_blastx_alignment(
                                            str(obj.output_filename)
                                        )

                        # 2. Remove only UserInput object. BlastDBData object
                        # will be deleted together. Remove zip
                        remove_database_data(
                            db_path, 
                            db_user_input.name_of_blast_db)

                        if not (
                        UserInput.objects.filter(
                            input_file=db_user_input.input_file
                        ).exclude(
                            name_of_blast_db=db_user_input.name_of_blast_db
                        ).exists()):
                            if not updated_dbs_files:
                                # Remove input file
                                remove_inputs(
                                    user_inputs_path,
                                    db_user_input.input_file
                                )
                                # Remove taxid map file
                                remove_inputs(
                                    user_taxid_files_path,
                                    db_user_input.taxid_map
                                )
                            
                    else:
                        # Child db is the only child
                        # 1. Remove alignment objects and input files
                        if(BlastnUserInput.objects \
                        .filter(database=db_object) \
                            .exists()):
                            # Retrieving objects
                            blastn_objects = BlastnUserInput.objects \
                                .filter(database=db_object)

                            # Looping through objects
                            if(blastn_objects):
                                for obj in blastn_objects:
                                    if(BlastnUserInput.objects
                                        .filter(query_file=obj.query_file)
                                        .exclude(output_filename=obj.output_filename) 
                                        .exists()):
                                        # Remove only output file
                                        remove_inputs(
                                            blastn_align_out, 
                                            obj.output_filename)
                                        obj.delete()
                                    else:
                                        # Removing files and object
                                        remove_blastn_alignment(
                                            str(obj.output_filename))

                        if(BlastpUserInput.objects \
                            .filter(database=db_object) \
                                .exists()):
                            # Retrieving objects
                            blastp_objects = BlastpUserInput.objects \
                                .filter(database=db_object)

                            # Looping through objects
                            if(blastp_objects):
                                for obj in blastp_objects:
                                    if(BlastpUserInput.objects \
                                        .filter(query_file=obj.query_file)
                                        .exclude(output_filename=obj.output_filename) 
                                        .exists()):
                                        # Remove only output file
                                        remove_inputs(
                                            blastp_align_out, 
                                            obj.output_filename)
                                        obj.delete()
                                    else:
                                        # Removing files and object
                                        remove_blastp_alignment(
                                            str(obj.output_filename))

                        if(tBlastxUserInput.objects \
                            .filter(database=db_object) \
                                .exists()):
                            # Retrieving objects
                            tblastx_objects = tBlastxUserInput.objects \
                                .filter(database=db_object)

                            # Looping through objects
                            if(tblastx_objects):
                                for obj in tblastx_objects:
                                    # If input file is used somewhere
                                    if(tBlastxUserInput.objects \
                                        .filter(query_file=obj.query_file)
                                        .exclude(output_filename=obj.output_filename) 
                                        .exists()):
                                        # Remove only output file
                                        remove_inputs(
                                            tblastx_align_out, 
                                            obj.output_filename)
                                        obj.delete()
                                    else:
                                        # Removing files and object
                                        remove_tblastx_alignment(
                                            str(obj.output_filename))

                        if(tBlastnUserInput.objects \
                            .filter(database=db_object) \
                                .exists()):
                            # Retrieving objects
                            tblastn_objects = tBlastnUserInput.objects \
                                .filter(database=db_object)

                            # Looping through objects
                            if(tblastn_objects):
                                for obj in tblastn_objects:
                                    # If input file is used 
                                    if(tBlastnUserInput.objects
                                        .filter(query_file=obj.query_file)
                                        .exclude(output_filename=obj.output_filename) 
                                        .exists()):
                                        # Remove only output file
                                        remove_inputs(
                                            tblastn_align_out, 
                                            obj.output_filename)
                                        obj.delete()
                                    else:
                                        # Removing files and object
                                        remove_tblastn_alignment(
                                            str(obj.output_filename))

                        if(BlastxUserInput.objects \
                            .filter(database=db_object) \
                                .exists()):
                            # Retrieving objects
                            blastx_obj = BlastxUserInput.objects \
                                .filter(database=db_object)

                            # Looping through objects
                            if(blastx_obj):
                                for obj in blastx_obj:
                                    # If input file is used 
                                    if(BlastxUserInput.objects
                                        .filter(query_file=obj.query_file)
                                        .exclude(output_filename=obj.output_filename) 
                                        .exists()):
                                        # Remove only output file
                                        remove_inputs(
                                            blastx_align_out, 
                                            obj.output_filename)
                                        obj.delete()
                                    else:
                                        # Removing files and object
                                        remove_blastx_alignment(
                                            str(obj.output_filename))


                        # 2. Removing database files and UserInput object
                        # BlastDBData will be deleted together with UserInput
                        # Remove zip file and its files 
                        remove_database_data(
                            db_path, 
                            db_user_input.name_of_blast_db)

                        if not (
                        UserInput.objects.filter(
                            input_file=db_user_input.input_file
                        ).exclude(
                            name_of_blast_db=db_user_input.name_of_blast_db
                        ).exists()):
                            if not updated_dbs_files:
                                # Remove input file
                                remove_inputs(
                                    user_inputs_path,
                                    db_user_input.input_file
                                )
                                # Remove taxid map file
                                remove_inputs(
                                    user_taxid_files_path,
                                    db_user_input.taxid_map
                                )

                    

@login_required(login_url='login')
def private_blastdb(request):
    if request.method == 'POST':
        db_names = request.POST.getlist('blast_db_names[]')
        if(db_names):
            for name in db_names:
                if(UserInput.objects.filter(name_of_blast_db=name).exists()):
                    founded_db = UserInput.objects.get(name_of_blast_db=name)
                    # Removing files from directories
                    remove_user_files(name)
                    # Removing object from database
                    founded_db.delete()

            logger.info(
                f"Selected BLAST databases were removed successfully."
            )

    # Rendering view of private BLAST databases, logged users
    blast_db_data = BlastDBData.objects \
        .filter(user_input__public_or_private="private")

    logger.info(
        f"Retrieval of BLAST databases objects "
        f"was successful."
    )

    context = {
        'blast_db_data': blast_db_data,
    }
    return render(request, "blast_db_creator/private_db.html", context)



def blastn_page(request, slug=None):
    obj = ''
    batch_align = ''
    try:
        obj = BlastDBData.objects.get(slug=slug)
    except BlastDBData.MultipleObjectsReturned:
        obj = BlastDBData.objects.filter(slug=slug).first()
    except BlastDBData.DoesNotExist:
        try:
            batch_align = BatchAlign.objects.filter(unique_db_index=slug)
        except BatchAlign.MultipleObjectsReturned:
            batch_align = BatchAlign.objects.filter(unique_db_index=slug)
        except: 
            raise Http404
        else:
            batch_align = BatchAlign.objects.filter(unique_db_index=slug)
    except:
        raise Http404
    else:
        obj = BlastDBData.objects.get(slug=slug)

    # Retrieving data from form and saving it to models
    if request.method == 'POST':
        form = BlastnForm(request.POST, request.FILES)
        if form.is_valid():
            if(obj):
                form.instance.database = obj
                form.instance.batch_align = None
                form.save()

                logger.info(
                    f"User input for similar search sequence using \"blastn\""
                    f" was saved successfully."
                )

                if request.user.is_authenticated:
                    # Initialize task in Celery
                    blastn_task.delay(slug, form.instance.output_filename,
                        False, request.user.username)

                    messages.info(request, (
                        f"Searching for similar sequences between the query "
                        f"sequence(s) and the BLAST database. "
                        f"When the processing is finished, "
                        f"the result will appear in "
                        f"the table. Please wait. "
                    ))
                    
                    # Redirect user to all task list to view the progress
                    return redirect('task_list')

                else:
                    error_blastn = run_blastn(slug, 
                        form.instance.output_filename, False)
                    created_obj = BlastnUserInput.objects \
                        .get(output_filename=form.instance.output_filename)
                    if error_blastn:
                        created_obj.delete()
                        messages.error(request, str(error_blastn))
                        logger.warning(
                            f"Could not search for similar sequences "
                            f"using \"blastn\" program."
                            f"Errors received: {error_blastn}."
                        )
                    else:
                        saveblastn_result(form.instance.output_filename)
                        logger.info(
                            f"Search for similar sequences using \"blastn\" "
                            f"program finished "
                            f"succesfully. ")

                        if(form.instance.database):
                            if form.instance.database.user_input:
                                if form.instance.database.user_input \
                                        .public_or_private == 'public':
                                    return redirect('blastresultpublic')
                                else:
                                    messages.error(request, "Private databases" 
                                    + " available for logged in users only.")
                                    return redirect('login')

            elif(batch_align):
                # Run blastn for batch_align
                
                if(len(form.instance.output_filename) == 100 or
                 len(form.instance.output_filename) > 100 - 4):
                    messages.error(request, (
                        f"The filename is too long to generate BLASTn "
                        f"alignments "
                        f"for each BLAST database selected. Filename has to be"
                        f" shorter than 97 symbols in order to generate the "
                        f"batch "
                        f"BLASTn alignments for many BLAST databases."))
                    return redirect('blastn', slug)

                batch_align_filenames = []

                # Generating all new BlastnUserInputs
                original_output_filename = form.instance.output_filename
                for db_obj in batch_align:
                    # Generating unique filename
                    output_filename = generate_unique_filename(
                    original_output_filename, BlastnUserInput)

                    # Inserting model field data and saving object
                    form.instance.database = db_obj.database
                    form.instance.output_filename = output_filename
                    form.instance.batch_align = db_obj
                    form.save()

                    # Appending filenames to the list for BLASTn program
                    batch_align_filenames.append(output_filename)

                # Initialize Celery task
                batch_blastn_alignments.delay(batch_align_filenames, slug,
                    request.user.username)
                
                messages.info(request, (
                    f"Searching for similar sequences between the query "
                    f"sequence(s) and the BLAST databases. "
                    f"When the processing is finished, "
                    f"the result will appear in "
                    f"the table."
                ))

                return redirect('task_list')

        else:
            context = {
                'object': obj,
                'form': form,
                'multi_align': batch_align,
                'slug': slug,
            }
            return render(request, 
                "blast_db_creator/blastn_page.html", context)

    else:
        form = BlastnForm()

    context = {
        'object': obj,
        'form': form,
        'multi_align': batch_align,
        'slug': slug,
    }
    return render(request, "blast_db_creator/blastn_page.html", context)


def blast_result_public(request):
    # getting all objects from models to send to template
    blastn_results = BlastnResults.objects \
        .filter(
            blastn_request__database__user_input__public_or_private="public"
        )
    blastp_results = BlastpResults.objects \
        .filter(
            blastp_request__database__user_input__public_or_private="public"
        )
    tblastn_results = tBlastnResults.objects \
        .filter(
            tblastn_request__database__user_input__public_or_private="public"
        )
    tblastx_results = tBlastxResults.objects \
        .filter(
            tblastx_request__database__user_input__public_or_private="public"
        )
    blastx_results = BlastxResults.objects \
        .filter(
            blastx_request__database__user_input__public_or_private="public"
        )

    logger.info(
        f"Retrieval of alignments results objects "
        f"were successful."
    )

    context = {
        'blastn_results': blastn_results,
        'blastp_results': blastp_results,
        'tblastn_results': tblastn_results,
        'tblastx_results': tblastx_results,
        'blastx_results': blastx_results,
    }

    return render(
        request, "blast_db_creator/blast_result_public.html", context)


def get_descendants(parent, parent_children_map):
    descendants = set()
    if parent in parent_children_map:
        for child in parent_children_map[parent]:
            descendants.add(child)
            descendants |= get_descendants(child, parent_children_map)
    return descendants if descendants else set()


def find_updatable_alignments(all_dbs, all_alignments):
    parent_children_map = {}
    parent_alignments = {}
    children_alignments = {}
    updated_alignments = {}
    to_align = {}

    logger.info(
        f"Retrieving alignments that can be updated."
    )

    # Retrieving all parents as keys
    for db in all_dbs:
        if db.father_database:
            parent_children_map[db.father_database.slug] = []
            parent_alignments[db.father_database.slug] = []

    # Filling up parent_children_map and retrieving child_alignment
    # and updated_alignments keys
    for db in all_dbs:
        for k in parent_children_map.keys():
            if db.father_database:
                if db.father_database.slug == k:
                    parent_children_map[k].append(db.slug)
                    children_alignments[db.slug] = []
                    updated_alignments[db.slug] = []

    # Filling up parent_alignments values
    for key in parent_alignments.keys():
        for align in all_alignments:
            if(hasattr(align, 'blastp_request')):
                if align.blastp_request.database is not None:
                    if align.blastp_request.database.slug == key:
                        parent_alignments[key].append(
                            align.blastp_request.output_filename)
            elif(hasattr(align, 'blastn_request')):
                if align.blastn_request.database is not None:
                    if align.blastn_request.database.slug == key:
                        parent_alignments[key].append(
                            align.blastn_request.output_filename)
            elif(hasattr(align, 'tblastx_request')):
                if align.tblastx_request.database is not None:
                    if align.tblastx_request.database.slug == key:
                        parent_alignments[key].append(
                            align.tblastx_request.output_filename)
            elif(hasattr(align, 'tblastn_request')):
                if align.tblastn_request.database is not None:
                    if align.tblastn_request.database.slug == key:
                        parent_alignments[key].append(
                            align.tblastn_request.output_filename)
            elif(hasattr(align, 'blastx_request')):
                if align.blastx_request.database is not None:
                    if align.blastx_request.database.slug == key:
                        parent_alignments[key].append(
                            align.blastx_request.output_filename)

    # Filling up children_alignments values
    for parent, children in parent_children_map.items():
        for child in children:
            for align in all_alignments:
                if(hasattr(align, 'blastp_request')):
                    if align.blastp_request.database is not None:
                        if align.blastp_request.database.slug == child:
                            children_alignments[child].append(
                                align.blastp_request.output_filename)
                elif(hasattr(align, 'blastn_request')):
                    if align.blastn_request.database is not None:
                        if align.blastn_request.database.slug == child:
                            children_alignments[child].append(
                                align.blastn_request.output_filename)
                elif(hasattr(align, 'tblastn_request')):
                    if align.tblastn_request.database is not None:
                        if align.tblastn_request.database.slug == child:
                            children_alignments[child].append(
                                align.tblastn_request.output_filename)
                elif(hasattr(align, 'tblastx_request')):
                    if align.tblastx_request.database is not None:
                        if align.tblastx_request.database.slug == child:
                            children_alignments[child].append(
                                align.tblastx_request.output_filename)
                elif(hasattr(align, 'blastx_request')):
                    if align.blastx_request.database is not None:
                        if align.blastx_request.database.slug == child:
                            children_alignments[child].append(
                                align.blastx_request.output_filename)

    # Remove empty key:values
    children_alignments_temp = children_alignments
    children_alignments = {}
    for child, alignments in children_alignments_temp.items():
        if alignments:
            children_alignments[child] = alignments

    # Search for alignments with matching query_file
    for parent, alignments in parent_alignments.items():
        for align in alignments:
            align_obj = ""
            if(BlastnUserInput.objects.filter(output_filename=align)
               .exists()):
                align_obj = str(BlastnUserInput.objects.filter(
                    output_filename=align).first().query_file)
            elif(BlastpUserInput.objects.filter(output_filename=align)
                 .exists()):
                align_obj = str(BlastpUserInput.objects.filter(
                    output_filename=align).first().query_file)
            elif(BlastxUserInput.objects.filter(output_filename=align)
                 .exists()):
                align_obj = str(BlastxUserInput.objects.filter(
                    output_filename=align).first().query_file)
            elif(tBlastxUserInput.objects.filter(output_filename=align)
                 .exists()):
                align_obj = str(tBlastxUserInput.objects.filter(
                    output_filename=align).first().query_file)
            elif(tBlastnUserInput.objects.filter(output_filename=align)
                 .exists()):
                align_obj = str(tBlastnUserInput.objects.filter(
                    output_filename=align).first().query_file)
            
            # Check if alignment input file matches in children alignments
            for child, c_alignments in children_alignments.items():
                for c_align in c_alignments:
                    child_align_obj = ""
                    if(BlastnUserInput.objects.filter(
                        output_filename=c_align).exists()):
                        child_align_obj = str(BlastnUserInput.objects.filter(
                            output_filename=c_align).first().query_file)
                    elif(BlastpUserInput.objects.filter(
                        output_filename=c_align).exists()):
                        child_align_obj = str(BlastpUserInput.objects.filter(
                            output_filename=c_align).first().query_file)
                    elif(BlastxUserInput.objects.filter(
                        output_filename=c_align).exists()):
                        child_align_obj = str(BlastxUserInput.objects.filter(
                            output_filename=c_align).first().query_file)
                    elif(tBlastnUserInput.objects.filter(
                        output_filename=c_align).exists()):
                        child_align_obj = str(tBlastnUserInput.objects.filter(
                            output_filename=c_align).first().query_file)
                    elif(tBlastxUserInput.objects.filter(
                        output_filename=c_align).exists()):
                        child_align_obj = str(tBlastxUserInput.objects.filter(
                            output_filename=c_align).first().query_file)

                    # If alignments match input_file
                    if(child_align_obj == align_obj):
                        # Retrieve all possible children that can be used 
                        # in update
                        ancestery = get_descendants(parent, parent_children_map)
                        if child in ancestery:
                            # It means it was updated
                            updated_alignments[child].append(align)

    # Remove empty keys:values
    temp_updated_alignments = updated_alignments
    updated_alignments = {}
    for child, alignments in temp_updated_alignments.items():
        if alignments:
            updated_alignments[child] = alignments


    for parent, alignments in parent_alignments.items():
        # Create dictionary with parents and alignments that need update
        to_align[parent] = []
        alignments_needed_update = []

        # Retrieve all possible children that can be used in update
        ancestery = get_descendants(parent, parent_children_map)

        # Looping through father alignments
        for align in alignments:
            for anc in ancestery:
                # If no children are present they don't have update
                if anc not in updated_alignments.keys():
                    to_align[parent].append(align)
                else:
                    # If there are children in updated_alignments,
                    # find which alignments are not updated using them
                    for child, p_alignments in updated_alignments.items():
                        if child == anc:
                            if align not in p_alignments:
                                to_align[parent].append(align)
    
    # Removing duplicates and empty values
    alignments_to_update = {}
    for key, values in to_align.items():
        filtered_values = list(set(filter(None, values)))
        if filtered_values:
            alignments_to_update[key] = filtered_values
            
    return alignments_to_update

def retrieve_prot_databases(all_databases):
    # Retrieve user inputs of protein databases
    prot_db_user_input = UserInput.objects.filter(database_type='prot')

    # Retrieve only protein databases
    prot_databases = []
    for db in all_databases:
        for prot_db_ui in prot_db_user_input:
            if db.user_input == prot_db_ui:
                if BlastDBData.objects.filter(slug=db.slug).exists():
                    prot_databases.append(db)

    logger.info(
        f"Retrieval of protein databases were successful."
    )
    
    return prot_databases

def retrieve_nucl_databases(all_databases):
    # Retrieve user inputs of nucl databases
    nucl_db_user_input = UserInput.objects.filter(database_type='nucl')

    # Retrieve only nucl databases
    nucl_databases = []
    for db in all_databases:
        for nucl_db_ui in nucl_db_user_input:
            if db.user_input == nucl_db_ui:
                if BlastDBData.objects.filter(slug=db.slug).exists():
                    nucl_databases.append(db)
    
    logger.info(
        f"Retrieval of nucleotide databases were successful."
    )

    return nucl_databases


def remove_alignments(request, alignment_names, output_path, 
    remove_alignment_func, alignment_model):
    for name in alignment_names:
        # Searching for alignment object
        founded_alignment = alignment_model.objects \
            .filter(output_filename=name).first()

        # If alignment was retrieved using batch retrieval using many DBs
        if founded_alignment.batch_align:
            batch_id = founded_alignment.batch_align.id
            unique_index = founded_alignment.batch_align.unique_db_index
            db_used = founded_alignment.database

            # Retrieve batch object
            batch_obj = BatchAlign.objects \
                .filter(id=batch_id) \
                .filter(database=db_used) \
                .first()

            # Retrieve all batch alignments with same id
            batch_objects = BatchAlign.objects \
                .filter(unique_db_index=unique_index)
            
            if batch_objects and batch_obj:
                if(len(batch_objects) > 1):
                    # Remove alignment result
                    remove_inputs(output_path, 
                        founded_alignment.output_filename)
                    # Remove objects
                    batch_obj.delete()
                    founded_alignment.delete()
                else:
                    # Remove input and alignment result and object
                    if(alignment_model 
                        .objects 
                        .filter(query_file=founded_alignment.query_file) 
                        .exclude(output_filename=founded_alignment.output_filename) 
                        .exists()):
                        # If perhaps batch alignment is used in update alignment
                        remove_inputs(
                            output_path, 
                            founded_alignment.output_filename)
                        batch_obj.delete()
                        founded_alignment.delete()
                    else:
                        remove_alignment_func(name)
                        # Remove batch object
                        batch_obj.delete()

        else:
            if(founded_alignment.database.father_database == None):
                # Father DB or just by itself was used for alignment
                if(alignment_model.objects.filter(
                    query_file=founded_alignment.query_file
                ).exclude(
                    output_filename=founded_alignment.output_filename
                ).exists()):
                    remove_inputs(output_path, 
                        founded_alignment.output_filename)
                    founded_alignment.delete()
                else:
                    remove_alignment_func(name)  
            else:
                # Children DB was used for alignment
                if(alignment_model.objects.filter(
                    query_file=founded_alignment.query_file
                ).exclude(
                    output_filename=founded_alignment.output_filename
                ).exists()):
                    remove_inputs(output_path, 
                        founded_alignment.output_filename)
                    founded_alignment.delete()
                else:
                    remove_alignment_func(name)  


@login_required(login_url='login')
def blast_result_user(request):
    if request.method == 'POST':
        blastn_alignments_names = request.POST.getlist(
            'blastn_alignment_names[]')
        blastp_alignments_names = request.POST.getlist(
            'blastp_alignment_names[]')
        tblastn_alignments_names = request.POST.getlist(
            'tblastn_alignment_names[]')
        tblastx_alignments_names = request.POST.getlist(
            'tblastx_alignment_names[]')
        blastx_alignments_names = request.POST.getlist(
            'blastx_alignment_names[]')

        # Creating a map to prepare for removal of specified alignments
        mapping = {
            'blastn': (
                blastn_alignments_names, 
                remove_blastn_alignment,
                BlastnUserInput
            ),
            'blastp': (
                blastp_alignments_names,
                remove_blastp_alignment, 
                BlastpUserInput
            ),
            'tblastn': (
                tblastn_alignments_names, 
                remove_tblastn_alignment, 
                tBlastnUserInput
            ),
            'tblastx': (
                tblastx_alignments_names, 
                remove_tblastx_alignment, 
                tBlastxUserInput
            ),
            'blastx': (
                blastx_alignments_names,
                remove_blastx_alignment, 
                BlastxUserInput
            )
        }

        for key, value in mapping.items():
            alignment_names, remove_alignment_func, alignment_model = value
            if alignment_names:
                if key == 'blastn':
                    output_path = 'media/blastn_outputs/'
                elif key == 'blastp':
                    output_path = 'media/blastp_outputs/'
                elif key == 'blastx':
                    output_path = 'media/blastx_outputs/'
                elif key == 'tblastx':
                    output_path = 'media/tblastx_outputs/'
                elif key == 'tblastn':
                    output_path = 'media/tblastn_outputs/'
                remove_alignments(
                    request, 
                    alignment_names, 
                    output_path, 
                    remove_alignment_func, 
                    alignment_model
                )

        logger.info(
            f"Removal of selected alignments results were successful."
        )

    # getting all objects from models to send to template
    blast_db_data = BlastDBData.objects \
        .filter(user_input__user=request.user)
    blastn_results = BlastnResults.objects \
        .filter(blastn_request__database__user_input__user=request.user)
    blastp_results = BlastpResults.objects \
        .filter(blastp_request__database__user_input__user=request.user)
    tblastn_results = tBlastnResults.objects \
        .filter(tblastn_request__database__user_input__user=request.user)
    tblastx_results = tBlastxResults.objects \
        .filter(tblastx_request__database__user_input__user=request.user)
    blastx_results = BlastxResults.objects \
        .filter(blastx_request__database__user_input__user=request.user)

    # Retrieve only Nucleotide or Protein databases
    prot_databases = retrieve_prot_databases(blast_db_data)
    nucl_databases = retrieve_nucl_databases(blast_db_data)
    
    # Retrieve alignments that can be updated
    to_update_blastp = find_updatable_alignments(
        prot_databases, 
        blastp_results)
    to_update_blastn = find_updatable_alignments(
        nucl_databases, 
        blastn_results)
    to_update_blastx = find_updatable_alignments(
        prot_databases, 
        blastx_results)
    to_update_tblastx = find_updatable_alignments(
        nucl_databases, 
        tblastx_results)
    to_update_tblastn = find_updatable_alignments(
        nucl_databases, 
        tblastn_results)

    context = {
        'blastn_results': blastn_results,
        'blastp_results': blastp_results,
        'to_update_blastn': to_update_blastn,
        'to_update_blastp': to_update_blastp,
        'to_update_blastx': to_update_blastx,
        'to_update_tblastx': to_update_tblastx,
        'to_update_tblastn': to_update_tblastn,
        'tblastn_results': tblastn_results,
        'tblastx_results': tblastx_results,
        'blastx_results': blastx_results,
    }

    return render(request, "blast_db_creator/blast_result_user.html", context)


def split_file_to_chunks(file_content):
    first_chunk = file_content.split("Query=")[0]
    other_chunks = file_content.split("Query=")
    all_chunks = other_chunks[1:]
    all_chunks = ["Query=" + chunk for chunk in all_chunks]
    all_chunks.insert(0, first_chunk)
    last_chunk = all_chunks.pop()
    last_two_chunks = last_chunk.split("  Database:")
    last_two_chunks[1] = "  Database:" + last_two_chunks[1]
    all_chunks.append(last_two_chunks[0])
    all_chunks.append(last_two_chunks[1])
    all_chunks = [chunk.strip() for chunk in all_chunks]
    return all_chunks


def view_task_result(request, slug=None):
    # Check whether blastn or blastp request
    obj_blastn = None
    obj_blastp = None
    obj_blastx = None
    obj_tblastn = None
    obj_tblastx = None

    try:
        obj_blastn = BlastnUserInput.objects.get(output_filename=slug)
    except BlastnUserInput.MultipleObjectsReturned:
        obj_blastn = BlastnUserInput.objects.filter(
            output_filename=slug).first()
    except BlastnUserInput.DoesNotExist:
        try:
            obj_blastp = BlastpUserInput.objects.get(output_filename=slug)
        except BlastpUserInput.MultipleObjectsReturned:
            obj_blastp = BlastpUserInput.objects.filter(
                output_filename=slug).first()
        except BlastpUserInput.DoesNotExist:
            try:
                obj_tblastn = tBlastnUserInput.objects.get(
                    output_filename=slug)
            except tBlastnUserInput.MultipleObjectsReturned:
                obj_tblastn = tBlastnUserInput.objects \
                    .filter(output_filename=slug).first()
            except tBlastnUserInput.DoesNotExist:
                try:
                    obj_tblastx = tBlastxUserInput.objects \
                        .get(output_filename=slug)
                except tBlastxUserInput.MultipleObjectsReturned:
                    obj_tblastx = tBlastxUserInput.objects \
                        .filter(output_filename=slug).first()
                except tBlastxUserInput.DoesNotExist:
                    try:
                        obj_blastx = BlastxUserInput.objects \
                            .get(output_filename=slug)
                    except BlastxUserInput.MultipleObjectsReturned:
                        obj_blastx = BlastxUserInput.objects \
                            .filter(output_filename=slug).first()
                    except BlastxUserInput.DoesNotExist:
                        raise Http404
                    except:
                        raise Http404
                    else:
                        obj_blastx = BlastxUserInput.objects \
                            .get(output_filename=slug)
                except:
                    raise Http404
                else:
                    obj_tblastx = tBlastxUserInput.objects \
                        .get(output_filename=slug)
            except:
                raise Http404
            else:
                obj_tblastn = tBlastnUserInput.objects.get(
                    output_filename=slug)
        except:
            raise Http404
        else:
            obj_blastp = BlastpUserInput.objects.get(output_filename=slug)
    except:
        raise Http404
    else:
        obj_blastn = BlastnUserInput.objects.get(output_filename=slug)

    logger.info(
        f"Viewing alignments results."
    )

    # depending on whether nucleotide or protein pairwise alignment
    if obj_blastn:
        obj_blastn_result = None
        try:
            obj_blastn_result = BlastnResults.objects. \
                get(blastn_request=obj_blastn.output_filename)
        except BlastnResults.DoesNotExist:
            raise Http404
        except BlastnResults.MultipleObjectsReturned:
            obj_blastn_result = BlastnResults.objects. \
                filter(blastn_request=obj_blastn.output_filename).first()
        except:
            raise Http404

        # send file contents to template
        if obj_blastn_result:
            if os.path.exists('media/' + str(obj_blastn_result.blastn_result)):
                file = open('media/' + str(obj_blastn_result.blastn_result),
                            'r')
                file_content = file.read()
                file.close()
                all_chunks = split_file_to_chunks(file_content)
            else:
                raise Http404

    elif obj_blastp:
        obj_blastp_result = None
        try:
            obj_blastp_result = BlastpResults.objects. \
                get(blastp_request=obj_blastp.output_filename)
        except BlastpResults.DoesNotExist:
            raise Http404
        except BlastpResults.MultipleObjectsReturned:
            obj_blastp_result = BlastpResults.objects. \
                filter(blastp_request=obj_blastp.output_filename).first()
        except:
            raise Http404
        # send file contents to template
        if obj_blastp_result:
            if os.path.exists('media/' + str(obj_blastp_result.blastp_result)):
                file = open('media/' + str(obj_blastp_result.blastp_result),
                            'r')
                file_content = file.read()
                file.close()
                all_chunks = split_file_to_chunks(file_content)
            else:
                raise Http404

    elif obj_blastx:
        obj_blastx_result = None
        try:
            obj_blastx_result = BlastxResults.objects. \
                get(blastx_request=obj_blastx.output_filename)
        except BlastxResults.DoesNotExist:
            raise Http404
        except BlastxResults.MultipleObjectsReturned:
            obj_blastx_result = BlastxResults.objects. \
                filter(blastx_request=obj_blastx.output_filename).first()
        except:
            raise Http404

        # send file contents to template
        if obj_blastx_result:
            if os.path.exists('media/' + str(obj_blastx_result.blastx_result)):
                file = open('media/' + str(obj_blastx_result.blastx_result),
                            'r')
                file_content = file.read()
                file.close()
                all_chunks = split_file_to_chunks(file_content)
            else:
                raise Http404

    elif obj_tblastx:
        obj_tblastx_result = None
        try:
            obj_tblastx_result = tBlastxResults.objects. \
                get(tblastx_request=obj_tblastx.output_filename)
        except tBlastxResults.DoesNotExist:
            raise Http404
        except tBlastxResults.MultipleObjectsReturned:
            obj_tblastx_result = tBlastxResults.objects. \
                filter(tblastx_request=obj_tblastx.output_filename).first()
        except:
            raise Http404

        # send file contents to template
        if obj_tblastx_result:
            if os.path.exists('media/' +
                              str(obj_tblastx_result.tblastx_result)):
                file = open('media/' + str(obj_tblastx_result.tblastx_result),
                            'r')
                file_content = file.read()
                file.close()
                all_chunks = split_file_to_chunks(file_content)
            else:
                raise Http404

    elif obj_tblastn:
        obj_tblastn_result = None
        try:
            obj_tblastn_result = tBlastnResults.objects. \
                get(tblastn_request=obj_tblastn.output_filename)
        except tBlastnResults.DoesNotExist:
            raise Http404
        except tBlastnResults.MultipleObjectsReturned:
            obj_tblastn_result = tBlastnResults.objects. \
                filter(tblastn_request=obj_tblastn.output_filename).first()
        except:
            raise Http404

        # send file contents to template
        if obj_tblastn_result:
            if os.path.exists('media/' +
                              str(obj_tblastn_result.tblastn_result)):
                file = open('media/' + str(obj_tblastn_result.tblastn_result),
                            'r')
                file_content = file.read()
                file.close()
                all_chunks = split_file_to_chunks(file_content)
            else:
                raise Http404

    context = {
        'file_content': all_chunks,
    }
    return render(request, "blast_db_creator/view_task_result.html", context)


def blastp_page(request, slug=None):
    obj = ''
    batch_align = ''
    try:
        obj = BlastDBData.objects.get(slug=slug)
    except BlastDBData.MultipleObjectsReturned:
        obj = BlastDBData.objects.filter(slug=slug).first()
    except BlastDBData.DoesNotExist:
        try:
            batch_align = BatchAlign.objects.filter(unique_db_index=slug)
        except BatchAlign.MultipleObjectsReturned:
            batch_align = BatchAlign.objects.filter(unique_db_index=slug)
        except: 
            raise Http404
        else:
            batch_align = BatchAlign.objects.filter(unique_db_index=slug)
    except:
        raise Http404
    else:
        obj = BlastDBData.objects.get(slug=slug)


    # Retrieving data from form and saving it to models
    if request.method == 'POST':
        form = BlastpForm(request.POST, request.FILES)
        if form.is_valid():
            if(obj):
                form.instance.database = obj
                form.instance.batch_align = None
                form.save()

                logger.info(
                    f"User input for similar search sequence using \"blastp\""
                    f" was saved successfully."
                )
                
                if request.user.is_authenticated:
                    # Initialize task in Celery
                    blastp_task.delay(slug, form.instance.output_filename,
                    False, request.user.username)

                    messages.info(request, (
                        f"Searching for similar sequences between the query "
                        f"sequence(s) and the BLAST database. "
                        f"When the processing is finished, "
                        f"the result will appear in "
                        f"the table. "
                    ))

                    # Redirect user to all task list to view the progress
                    return redirect('task_list')

                else:
                    error_blastp = run_blastp(slug, 
                        form.instance.output_filename, False)
                    created_obj = BlastpUserInput.objects \
                        .get(output_filename=form.instance.output_filename)
                    if error_blastp:
                        # deleting object from model if any error occured
                        created_obj.delete()
                        messages.error(request, str(error_blastp))
                        logger.warning(
                            f"Could not search for similar sequences "
                            f"using \"blastp\" program."
                            f"Errors received: {error_blastp}."
                        )
                    else:
                        saveblastp_result(form.instance.output_filename)
                        logger.info(
                            f"Search for similar sequences using \"blastp\" "
                            f"program finished "
                            f"succesfully. ")
                        if(form.instance.database):
                            if form.instance.database.user_input:
                                if form.instance.database.user_input \
                                        .public_or_private == 'public':
                                    return redirect('blastresultpublic')
                                else:
                                    messages.error(request, "Private databases" 
                                    + " available for logged in users only.")
                                    return redirect('login')

            elif(batch_align):
                # Run blastp for batch_align
                
                if(len(form.instance.output_filename) == 100 or
                 len(form.instance.output_filename) > 100 - 4):
                    messages.error(request, (
                        f"The filename is too long to generate BLASTp "
                        f"alignments "
                        f"for each BLAST database selected. Filename has to be"
                        f" shorter than 97 symbols in order to generate the "
                        f"batch "
                        f"BLASTp alignments for many BLAST databases."))
                    return redirect('blastp', slug)

                batch_align_filenames = []
                
                # Generating all new BlastpUserInputs
                original_output_filename = form.instance.output_filename
                for db_obj in batch_align:
                    # Creating new object for every database selected

                    # Generating unique filename
                    output_filename = generate_unique_filename(
                    original_output_filename, BlastpUserInput)

                    # Inserting model field data and saving object
                    form.instance.database = db_obj.database
                    form.instance.output_filename = output_filename
                    form.instance.batch_align = db_obj
                    form.save()

                    batch_align_filenames.append(output_filename)

                # Initialize Celery task
                batch_blastp_alignments.delay(batch_align_filenames, slug,
                    request.user.username)

                messages.info(request, (
                    f"Searching for similar sequences between the query "
                    f"sequence(s) and the BLAST databases. "
                    f"When the processing is finished, "
                    f"the result will appear in "
                    f"the table. "
                ))

                return redirect('task_list')
        else:
            context = {
                'object': obj,
                'form': form,
                'multi_align': batch_align,
                'slug': slug,
            }
            return render(request, 
                "blast_db_creator/blastp_page.html", context)


    else:
        form = BlastpForm()

    context = {
        'object': obj,
        'form': form,
        'multi_align': batch_align,
        'slug': slug,
    }
    return render(request, "blast_db_creator/blastp_page.html", context)


def usage(request):
    # Rendering usage view
    return render(request, "blast_db_creator/usage.html")


def blastx_page(request, slug=None):
    # blastx page view function
    obj = ''
    batch_align = ''
    try:
        obj = BlastDBData.objects.get(slug=slug)
    except BlastDBData.MultipleObjectsReturned:
        obj = BlastDBData.objects.filter(slug=slug).first()
    except BlastDBData.DoesNotExist:
        try:
            batch_align = BatchAlign.objects.filter(unique_db_index=slug)
        except BatchAlign.MultipleObjectsReturned:
            batch_align = BatchAlign.objects.filter(unique_db_index=slug)
        except: 
            raise Http404
        else:
            batch_align = BatchAlign.objects.filter(unique_db_index=slug)
    except:
        raise Http404
    else:
        obj = BlastDBData.objects.get(slug=slug)

    # Retrieving data from form and saving it to models
    if request.method == 'POST':
        form = BlastxForm(request.POST, request.FILES)
        if form.is_valid():
            if(obj):
                form.instance.database = obj
                form.instance.batch_align = None
                form.save()

                logger.info(
                    f"User input for similar search sequence using \"blastx\""
                    f" was saved successfully."
                )

                if request.user.is_authenticated:    
                    # Initialize task in Celery
                    blastx_task.delay(slug, form.instance.output_filename,
                    False, request.user.username)

                    messages.info(request, (
                        f"Searching for similar sequences between the query "
                        f"sequence(s) and the BLAST database. "
                        f"When the processing is finished, "
                        f"the result will appear in "
                        f"the table. "
                    ))
                
                    # Redirect user to all task list to view the progress
                    return redirect('task_list')

                else:
                    error_blastx = run_blastx(slug, 
                        form.instance.output_filename, False)
                    created_obj = BlastxUserInput.objects \
                        .get(output_filename=form.instance.output_filename)
                    if error_blastx:
                        # deleting object from model if any error occured
                        created_obj.delete()
                        messages.error(request, str(error_blastx))
                        logger.warning(
                            f"Could not search for similar sequences "
                            f"using \"blastx\" program."
                            f"Errors received: {error_blastx}."
                        )
                    else:
                        saveblastx_result(form.instance.output_filename)
                        logger.info(
                            f"Search for similar sequences using \"blastx\" "
                            f"program finished "
                            f"succesfully. ")
                        if(form.instance.database):
                            if form.instance.database.user_input:
                                if form.instance.database.user_input \
                                        .public_or_private == 'public':
                                    return redirect('blastresultpublic')
                                else:
                                    messages.error(request, "Private databases" 
                                    + " available for logged in users only.")
                                    return redirect('login')
                
            elif(batch_align):
                # Run blastx for batch_align

                if(len(form.instance.output_filename) == 100 or
                 len(form.instance.output_filename) > 100 - 4):
                    messages.error(request, (
                        f"The filename is too long to generate BLASTx "
                        f"alignments "
                        f"for each BLAST database selected. Filename has to be"
                        f" shorter than 97 symbols in order to generate the "
                        f"batch "
                        f"BLASTx alignments for many BLAST databases."))
                    return redirect('blastx', slug)

                batch_align_filenames = []

                # Generating all new BlastxUserInputs
                original_output_filename = form.instance.output_filename
                for db_obj in batch_align:
                    # Creating new object for every database selected

                    # Generating unique filename for each db_obj
                    output_filename = generate_unique_filename(
                    original_output_filename, BlastxUserInput)

                    # Saving obj data to model
                    form.instance.database = db_obj.database
                    form.instance.output_filename = output_filename
                    form.instance.batch_align = db_obj
                    form.save()

                    # Appending filenames to the list for BLASTx program
                    batch_align_filenames.append(output_filename)

                # Initialize Celery task
                batch_blastx_alignments.delay(batch_align_filenames, slug,
                    request.user.username)

                messages.info(request, (
                    f"Searching for similar sequences between the query "
                    f"sequence(s) and the BLAST databases. "
                    f"When the processing is finished, "
                    f"the result will appear in "
                    f"the table. "
                ))

                return redirect('task_list')
        else:
            context = {
                'object': obj,
                'form': form,
                'multi_align': batch_align,
                'slug': slug,
            }

            return render(request, 
                "blast_db_creator/blastx_page.html", context)

    else:
        form = BlastxForm()

    context = {
        'object': obj,
        'form': form,
        'multi_align': batch_align,
        'slug': slug,
    }

    return render(request, "blast_db_creator/blastx_page.html", context)


def tblastx_page(request, slug=None):
    obj = ''
    batch_align = ''
    try:
        obj = BlastDBData.objects.get(slug=slug)
    except BlastDBData.MultipleObjectsReturned:
        obj = BlastDBData.objects.filter(slug=slug).first()
    except BlastDBData.DoesNotExist:
        try:
            batch_align = BatchAlign.objects.filter(unique_db_index=slug)
        except BatchAlign.MultipleObjectsReturned:
            batch_align = BatchAlign.objects.filter(unique_db_index=slug)
        except: 
            raise Http404
        else:
            batch_align = BatchAlign.objects.filter(unique_db_index=slug)
    except:
        raise Http404
    else:
        obj = BlastDBData.objects.get(slug=slug)

    # Retrieving data from form and saving it to models
    if request.method == 'POST':
        form = tBlastxForm(request.POST, request.FILES)
        if form.is_valid():
            if(obj):
                form.instance.database = obj
                form.instance.batch_align = None
                form.save()

                logger.info(
                    f"User input for similar search sequence using \"tblastx\""
                    f" was saved successfully."
                )

                if request.user.is_authenticated:
                    # Initialize task in Celery
                    tblastx_task.delay(slug, form.instance.output_filename,
                    False, request.user.username)

                    messages.info(request, (
                        f"Searching for similar sequences between the query "
                        f"sequence(s) and the BLAST database. "
                        f"When the processing is finished, "
                        f"the result will appear in "
                        f"the table. "
                    ))

                    # Redirect user to all task list to view the progress
                    return redirect('task_list')

                else:
                    error_tblastx = run_tblastx(slug, 
                        form.instance.output_filename, False)
                    created_obj = tBlastxUserInput.objects \
                        .get(output_filename=form.instance.output_filename)
                    if error_tblastx:
                        # deleting object from model if any error occured
                        created_obj.delete()
                        messages.error(request, str(error_tblastx))
                        logger.warning(
                            f"Could not search for similar sequences "
                            f"using \"tblastx\" program."
                            f"Errors received: {error_tblastx}."
                        )
                    else:
                        savetblastx_result(form.instance.output_filename)
                        logger.info(
                            f"Search for similar sequences using \"tblastx\" "
                            f"program finished "
                            f"succesfully. ")
                        if(form.instance.database):
                            if form.instance.database.user_input:
                                if form.instance.database.user_input \
                                        .public_or_private == 'public':
                                    return redirect('blastresultpublic')
                                else:
                                    messages.error(request, "Private databases" 
                                    + " available for logged in users only.")
                                    return redirect('login')


            elif(batch_align):
                # Run tblastx for batch_align

                if(len(form.instance.output_filename) == 100 or
                 len(form.instance.output_filename) > 100 - 4):
                    messages.error(request, (
                        f"The filename is too long to generate tBLASTx "
                        f"alignments "
                        f"for each BLAST database selected. Filename has to be"
                        f" shorter than 97 symbols in order to generate the "
                        f"batch "
                        f"tBLASTx alignments for many BLAST databases."))
                    return redirect('tblastx', slug)

                batch_align_filenames = []

                # Generating all new tBlastxUserInputs
                original_output_filename = form.instance.output_filename
                for db_obj in batch_align:
                    # Creating new object for every database selected

                    # Generating unique filename
                    output_filename = generate_unique_filename(
                    original_output_filename, tBlastxUserInput)

                    # Inserting model field data and saving object
                    form.instance.database = db_obj.database
                    form.instance.output_filename = output_filename
                    form.instance.batch_align = db_obj
                    form.save()

                    # Appending filenames to the list for tBLASTx program
                    batch_align_filenames.append(output_filename)

                # Initialize Celery task
                batch_tblastx_alignments.delay(batch_align_filenames, slug,
                    request.user.username)

                messages.info(request, (
                    f"Searching for similar sequences between the query "
                    f"sequence(s) and the BLAST databases. "
                    f"When the processing is finished, "
                    f"the result will appear in "
                    f"the table. "
                ))
                
                return redirect('task_list')
        else:
            context = {
                'object': obj,
                'form': form,
                'multi_align': batch_align,
                'slug': slug,
            }

            return render(request, 
                "blast_db_creator/tblastx_page.html", context)

    else:
        form = tBlastxForm()

    context = {
        'object': obj,
        'form': form,
        'multi_align': batch_align,
        'slug': slug,
    }

    return render(request, "blast_db_creator/tblastx_page.html", context)


def tblastn_page(request, slug=None):
    obj = ''
    batch_align = ''
    try:
        obj = BlastDBData.objects.get(slug=slug)
    except BlastDBData.MultipleObjectsReturned:
        obj = BlastDBData.objects.filter(slug=slug).first()
    except BlastDBData.DoesNotExist:
        try:
            batch_align = BatchAlign.objects.filter(unique_db_index=slug)
        except BatchAlign.MultipleObjectsReturned:
            batch_align = BatchAlign.objects.filter(unique_db_index=slug)
        except: 
            raise Http404
        else:
            batch_align = BatchAlign.objects.filter(unique_db_index=slug)
    except:
        raise Http404
    else:
        obj = BlastDBData.objects.get(slug=slug)

        # Retrieving data from form and saving it to models
    if request.method == 'POST':
        form = tBlastnForm(request.POST, request.FILES)
        if form.is_valid():
            if(obj):
                form.instance.database = obj
                form.instance.batch_align = None
                form.save()

                logger.info(
                    f"User input for similar search sequence using \"tblastn\""
                    f" was saved successfully."
                )

                if request.user.is_authenticated:
                    # Initialize task in Celery
                    tblastn_task.delay(slug, form.instance.output_filename,
                    False, request.user.username)

                    messages.info(request, (
                        f"Searching for similar sequences between the query "
                        f"sequence(s) and the BLAST database. "
                        f"When the processing is finished, "
                        f"the result will appear in "
                        f"the table. "
                    ))

                    # Redirect user to all task list to view the progress
                    return redirect('task_list')

                else:
                    error_tblastn = run_tblastn(slug, 
                        form.instance.output_filename, False)
                    created_obj = tBlastnUserInput.objects \
                        .get(output_filename=form.instance.output_filename)
                    if error_tblastn:
                        # deleting object from model if any error occured
                        created_obj.delete()
                        messages.error(request, str(error_tblastn))
                        logger.warning(
                            f"Could not search for similar sequences "
                            f"using \"tblastn\" program."
                            f"Errors received: {error_tblastn}."
                        )
                    else:
                        savetblastn_result(form.instance.output_filename)
                        logger.info(
                            f"Search for similar sequences using \"tblastn\" "
                            f"program finished "
                            f"succesfully. ")
                        if(form.instance.database):
                            if form.instance.database.user_input:
                                if form.instance.database.user_input \
                                        .public_or_private == 'public':
                                    return redirect('blastresultpublic')
                                else:
                                    messages.error(request, "Private databases" 
                                    + " available for logged in users only.")
                                    return redirect('login')

            elif(batch_align):
                # Run tblastn for batch_align
                
                if(len(form.instance.output_filename) == 100 or
                 len(form.instance.output_filename) > 100 - 4):
                    messages.error(request, (
                        f"The filename is too long to generate tBLASTn "
                        f"alignments "
                        f"for each BLAST database selected. Filename has to be"
                        f" shorter than 97 symbols in order to generate the "
                        f"batch "
                        f"tBLASTn alignments for many BLAST databases."))
                    return redirect('tblastn', slug)

                batch_align_filenames = []

                # Generating all new tBlastnUserInputs
                original_output_filename = form.instance.output_filename
                for db_obj in batch_align:
                    # Creating new object for every database selected

                    # Generating unique filename
                    output_filename = generate_unique_filename(
                    original_output_filename, tBlastnUserInput)

                    # Inserting model field data and saving object
                    form.instance.database = db_obj.database
                    form.instance.output_filename = output_filename
                    form.instance.batch_align = db_obj
                    form.save()

                    # Appending filenames to the list for tBLASTn program
                    batch_align_filenames.append(output_filename)

                # Initialize Celery task
                batch_tblastn_alignments.delay(batch_align_filenames, slug,
                    request.user.username)

                messages.info(request, (
                    f"Searching for similar sequences between the query "
                    f"sequence(s) and the BLAST databases. "
                    f"When the processing is finished, "
                    f"the result will appear in "
                    f"the table. "
                ))

                return redirect('task_list')
        else:
            context = {
                'object': obj,
                'form': form,
                'multi_align': batch_align,
                'slug': slug,
            }

            return render(request,
                "blast_db_creator/tblastn_page.html", context)

    else:
        form = tBlastnForm()

    context = {
        'object': obj,
        'form': form,
        'multi_align': batch_align,
        'slug': slug,
    }

    return render(request, "blast_db_creator/tblastn_page.html", context)


def is_unique_filename(db_name):
    logger.info(
        f"Generating unique filename"
    )
    # Generate random new string of length 4
    random_4 = string.ascii_letters + string.digits
    random.seed = (os.urandom(1024))
    random_id = "".join(random.choice(random_4) for i in range(4))
    # Generate new filename
    filename = F'{db_name}-updated-{random_id}.fasta'
    # Adding url to find maching filenames
    temp_filename = "blast_db_updates/" + filename
    if(UserInput.objects.filter(input_file=temp_filename).exists()):
        # If such filename already exists, run recursion
        is_unique_filename(db_name)
    else:
        # If such filename does not exist, return
        return filename


def update_with_text(data, db_name):
    logger.info(
        f"Creating a FASTA file from user input inserted text."
    )
    # Retrieve unique filename
    filename = is_unique_filename(db_name)
    # Saving uploaded text to file
    update_file = open("media/blast_db_updates/" + filename, 'w')
    update_file.write(data)
    update_file.close()

    # Check if file is smaller or equal to 1 MB
    if(os.path.getsize("media/blast_db_updates/" + filename) > 1000000):
        messages.error("The file that was provided in is larger than 1 MB. " +
                       "Please paste in file that is smaller" +
                       " or equal to 1 MB in size.")
        return False
    else:
        return "blast_db_updates/" + filename

def generate_unique_db_index():
    choose_from = string.ascii_letters.lower() + string.digits
    random.seed = (os.urandom(1024))
    db_index = "".join(random.choice(choose_from) for i in range(6))

    if(BatchAlign.objects.filter(unique_db_index=db_index).exists()):
        generate_unique_db_index()
    else:
        return db_index

def save_blastdb_update(father, in_file):
    father_object = UserInput.objects.get(
        name_of_blast_db=father.user_input.name_of_blast_db)
    father_object.input_file = in_file
    father_object.created = timezone.now()
    father_object.save()

    name = father_object.name_of_blast_db
    
    UserInput.objects.filter(name_of_blast_db=father_object.name_of_blast_db) \
        .update(name_of_blast_db=name, database_title=name)

    child_user_input = UserInput.objects.get(name_of_blast_db=name)
    return child_user_input

def save_specific_alignment_update(db_to_use, alignment_to_update):
    filename = alignment_to_update.output_filename
    if(db_to_use.user_input.database_type == 'prot'):
        alignment_to_update.database = db_to_use
        alignment_to_update.batch_align = None
        alignment_to_update.created = timezone.now()
        alignment_to_update.save()
        if(len(filename) > 100 - 4 or 
            len(filename) == 100):
                return "Reached limit of alignment updates to " + \
                " this alignment. The output filename is too long." + \
                " Alignment results filenames can only contain 100 characters."
        else:
            return alignment_to_update

    elif(db_to_use.user_input.database_type == 'nucl'):
        alignment_to_update.database = db_to_use
        alignment_to_update.batch_align = None
        alignment_to_update.created = timezone.now()
        alignment_to_update.save()
        if(len(filename) > 100 - 4 or 
            len(filename) == 100):
                return "Reached limit of alignment updates to " + \
                " this alignment. The output filename is too long." + \
                " Alignment results filenames can only contain 100 characters."
        else:
            return alignment_to_update


def find_child_db_to_update_alignment(all_dbs, all_alignments):
    logger.info(
        f"Searching for child BLAST databases that can be used for alignments"
        f" update. "
    )
    parent_children_map = {}
    parent_alignments = {}
    children_alignments = {}
    updated_alignments = {}
    to_use_for_update = {}

    # Retrieving all parents as keys
    for db in all_dbs:
        if db.father_database:
            parent_children_map[db.father_database.slug] = []
            parent_alignments[db.father_database.slug] = []

    # Filling up parent_children_map and retrieving child_alignment
    # and updated_alignments keys
    for db in all_dbs:
        for k in parent_children_map.keys():
            if db.father_database:
                if db.father_database.slug == k:
                    parent_children_map[k].append(db.slug)
                    children_alignments[db.slug] = []
                    updated_alignments[db.slug] = []

    # Filling up parent_alignments values and adding alignments as keys
    # to_use_for_update
    for key in parent_alignments.keys():
        for align in all_alignments:
            if(hasattr(align, 'blastp_request')):
                if align.blastp_request.database is not None:
                    if align.blastp_request.database.slug == key:
                        parent_alignments[key].append(
                            align.blastp_request.output_filename)
                        to_use_for_update[align.blastp_request
                        .output_filename] = []
            elif(hasattr(align, 'blastn_request')):
                if align.blastn_request.database is not None:
                    if align.blastn_request.database.slug == key:
                        parent_alignments[key].append(
                            align.blastn_request.output_filename)
                        to_use_for_update[align.blastn_request
                        .output_filename] = []
            elif(hasattr(align, 'tblastx_request')):
                if align.tblastx_request.database is not None:
                    if align.tblastx_request.database.slug == key:
                        parent_alignments[key].append(
                            align.tblastx_request.output_filename)
                        to_use_for_update[align.tblastx_request
                        .output_filename] = []
            elif(hasattr(align, 'tblastn_request')):
                if align.tblastn_request.database is not None:
                    if align.tblastn_request.database.slug == key:
                        parent_alignments[key].append(
                            align.tblastn_request.output_filename)
                        to_use_for_update[align.tblastn_request
                        .output_filename] = []
            elif(hasattr(align, 'blastx_request')):
                if align.blastx_request.database is not None:
                    if align.blastx_request.database.slug == key:
                        parent_alignments[key].append(
                            align.blastx_request.output_filename)
                        to_use_for_update[align.blastx_request
                        .output_filename] = []

    # Filling up children_alignments values
    for parent, children in parent_children_map.items():
        for child in children:
            for align in all_alignments:
                if(hasattr(align, 'blastp_request')):
                    if align.blastp_request.database is not None:
                        if align.blastp_request.database.slug == child:
                            children_alignments[child].append(
                                align.blastp_request.output_filename)
                elif(hasattr(align, 'blastn_request')):
                    if align.blastn_request.database is not None:
                        if align.blastn_request.database.slug == child:
                            children_alignments[child].append(
                                align.blastn_request.output_filename)
                elif(hasattr(align, 'tblastn_request')):
                    if align.tblastn_request.database is not None:
                        if align.tblastn_request.database.slug == child:
                            children_alignments[child].append(
                                align.tblastn_request.output_filename)
                elif(hasattr(align, 'tblastx_request')):
                    if align.tblastx_request.database is not None:
                        if align.tblastx_request.database.slug == child:
                            children_alignments[child].append(
                                align.tblastx_request.output_filename)
                elif(hasattr(align, 'blastx_request')):
                    if align.blastx_request.database is not None:
                        if align.blastx_request.database.slug == child:
                            children_alignments[child].append(
                                align.blastx_request.output_filename)

    # Remove empty key:values
    children_alignments_temp = children_alignments
    children_alignments = {}
    for child, alignments in children_alignments_temp.items():
        if alignments:
            children_alignments[child] = alignments

    # Search for alignments with matching query_file
    for parent, alignments in parent_alignments.items():
        for align in alignments:
            align_obj = ""
            if(BlastnUserInput.objects.filter(output_filename=align).exists()):
                align_obj = str(BlastnUserInput.objects.filter(
                    output_filename=align).first().query_file)
            elif(BlastpUserInput.objects \
                .filter(output_filename=align).exists()):
                align_obj = str(BlastpUserInput.objects.filter(
                    output_filename=align).first().query_file)
            elif(BlastxUserInput.objects.filter(output_filename=align)
                 .exists()):
                align_obj = str(BlastxUserInput.objects.filter(
                    output_filename=align).first().query_file)
            elif(tBlastxUserInput.objects.filter(output_filename=align)
                 .exists()):
                align_obj = str(tBlastxUserInput.objects.filter(
                    output_filename=align).first().query_file)
            elif(tBlastnUserInput.objects.filter(output_filename=align)
                 .exists()):
                align_obj = str(tBlastnUserInput.objects.filter(
                    output_filename=align).first().query_file)
                
            # Check if alignment input file matches in children alignments
            for child, c_alignments in children_alignments.items():
                for c_align in c_alignments:
                    child_align_obj = ""
                    if(BlastnUserInput.objects.filter(
                        output_filename=c_align).exists()):
                        child_align_obj = str(BlastnUserInput.objects.filter(
                            output_filename=c_align).first().query_file)
                    elif(BlastpUserInput.objects.filter(
                        output_filename=c_align).exists()):
                        child_align_obj = str(BlastpUserInput.objects.filter(
                            output_filename=c_align).first().query_file)
                    elif(BlastxUserInput.objects.filter(
                        output_filename=c_align).exists()):
                        child_align_obj = str(BlastxUserInput.objects.filter(
                            output_filename=c_align).first().query_file)
                    elif(tBlastnUserInput.objects.filter(
                        output_filename=c_align).exists()):
                        child_align_obj = str(tBlastnUserInput.objects.filter(
                            output_filename=c_align).first().query_file)
                    elif(tBlastxUserInput.objects.filter(
                        output_filename=c_align).exists()):
                        child_align_obj = str(tBlastxUserInput.objects.filter(
                            output_filename=c_align).first().query_file)

                    # If alignments match input_file
                    if(child_align_obj == align_obj):
                        # Retrieve all possible children that can be used 
                        # in update
                        ancestery = get_descendants(
                            parent, 
                            parent_children_map)

                        if child in ancestery:
                            # It means it was updated
                            updated_alignments[child].append(align)

    # Remove empty keys:values
    temp_updated_alignments = updated_alignments
    updated_alignments = {}
    for child, alignments in temp_updated_alignments.items():
        if alignments:
            updated_alignments[child] = alignments

    for parent, alignments in parent_alignments.items():
        # Retrieve all possible children that can be used in update
        ancestery = get_descendants(parent, parent_children_map)

        # Looping through father alignments
        for align in alignments:
            for anc in ancestery:
                # If no children are present they don't have update
                if anc not in updated_alignments.keys():
                    to_use_for_update[align].append(anc)
                else:
                    # If there are children in updated_alignments,
                    # find which alignments are not updated using them
                    for child, p_alignments in updated_alignments.items():
                        if child == anc:
                            if align not in p_alignments:
                                to_use_for_update[align].append(child)

    # Removing duplicates and empty values
    use_for_update = {}
    for key, values in to_use_for_update.items():
        filtered_values = list(set(filter(None, values)))
        if filtered_values:
            use_for_update[key] = filtered_values


    return use_for_update

@login_required(login_url='login')   
def update_alignment(request, slug=None):
    try:
        obj = BlastpUserInput.objects.get(output_filename=slug)
    except BlastpUserInput.MultipleObjectsReturned:
        obj = BlastpUserInput.objects.filter(output_filename=slug).first()
    except BlastpUserInput.DoesNotExist:
        try:
            obj = BlastnUserInput.objects.get(output_filename=slug)
        except BlastnUserInput.MultipleObjectsReturned:
            obj = BlastnUserInput.objects.filter(output_filename=slug).first()
        except BlastnUserInput.DoesNotExist:
            try:
                obj = BlastxUserInput.objects.get(output_filename=slug)
            except BlastxUserInput.MultipleObjectsReturned:
                obj = BlastxUserInput.objects \
                    .filter(output_filename=slug).first()
            except BlastxUserInput.DoesNotExist:
                try:
                    obj = tBlastxUserInput.objects.get(output_filename=slug)
                except tBlastxUserInput.MultipleObjectsReturned:
                    obj = tBlastxUserInput.objects \
                        .filter(output_filename=slug).first()
                except tBlastxUserInput.DoesNotExist:
                    try:
                        obj = tBlastnUserInput.objects \
                            .get(output_filename=slug)
                    except tBlastnUserInput.MultipleObjectsReturned:
                        obj = tBlastnUserInput.objects \
                            .filter(output_filename=slug).first()
                    except tBlastnUserInput.DoesNotExist:
                        raise Http404
                    except:
                        raise Http404
                except:
                    raise Http404
            except:
                raise Http404
        except:
            raise Http404
    except:
        raise Http404


    to_align_blastn = []
    to_align_blastp = []
    to_align_tblastn = []
    to_align_tblastx = []
    to_align_blastx = []

    blast_db_data = BlastDBData.objects.filter(user_input__user=request.user)    
    prot_databases = retrieve_prot_databases(blast_db_data)
    nucl_databases = retrieve_nucl_databases(blast_db_data)

    if isinstance(obj, BlastnUserInput):
        blastn_results = BlastnResults.objects \
        .filter(blastn_request__database__user_input__user=request.user)
        to_align_blastn = find_child_db_to_update_alignment(
            nucl_databases, blastn_results)

    elif isinstance(obj, BlastpUserInput):
        blastp_results = BlastpResults.objects \
        .filter(blastp_request__database__user_input__user=request.user)
        to_align_blastp = find_child_db_to_update_alignment(
            prot_databases, blastp_results)

    elif isinstance(obj, tBlastnUserInput):
        tblastn_results = tBlastnResults.objects \
        .filter(tblastn_request__database__user_input__user=request.user)
        to_align_tblastn = find_child_db_to_update_alignment(
            nucl_databases, tblastn_results)

    elif isinstance(obj, tBlastxUserInput):
        tblastx_results = tBlastxResults.objects \
        .filter(tblastx_request__database__user_input__user=request.user)
        to_align_tblastx = find_child_db_to_update_alignment(
            nucl_databases, tblastx_results)
        
    elif isinstance(obj, BlastxUserInput):
        blastx_results = BlastxResults.objects \
        .filter(blastx_request__database__user_input__user=request.user)
        to_align_blastx = find_child_db_to_update_alignment(
        prot_databases, blastx_results)


    if request.method == 'POST':
        selected_db = request.POST.get('db_name')
        if(selected_db):
            updated_db_user_input = UserInput.objects \
                .get(name_of_blast_db=selected_db)
            updated_db = BlastDBData.objects \
                .get(slug=selected_db)
            if(updated_db_user_input.database_type == 'prot'):
                alignment_user_in = save_specific_alignment_update(
                    updated_db,
                    obj)

                if isinstance(alignment_user_in, str): 
                    messages.error(request, str(alignment_user_in))
                    redirect_url = reverse('blastresultuser')
                    return JsonResponse({'success': False, 
                        'redirect_url': redirect_url})
                else:
                    if(BlastpUserInput.objects.filter(
                        output_filename=alignment_user_in.output_filename)
                        .exists()):

                        # Initialize Celery task
                        blastp_update_task.delay(
                            updated_db.slug,
                            alignment_user_in.output_filename,
                            True,
                            request.user.username
                        )

                        messages.info(request, (
                            f"Updating the selected alignment using updated" 
                            f" (child) BLAST database. "
                            f"When the processing is finished, "
                            f"the result will appear in "
                            f"the table. "
                        ))


                        # Redirect user to all task list to view the progress
                        redirect_url = reverse('task_list')
                        return JsonResponse({
                            'success': True, 
                            'redirect_url': redirect_url
                            })

                    elif(BlastxUserInput.objects.filter(
                        output_filename=alignment_user_in.output_filename)
                        .exists()):

                        # Initialize Celery task
                        blastx_update_task.delay(
                            updated_db.slug,
                            alignment_user_in.output_filename,
                            True,
                            request.user.username
                        )

                        messages.info(request, (
                            f"Updating the selected alignment using updated" 
                            f" (child) BLAST database. "
                            f"When the processing is finished, "
                            f"the result will appear in "
                            f"the table. "
                        ))

                        # Redirect user to all task list to view the progress
                        redirect_url = reverse('task_list')
                        return JsonResponse({
                            'success': True, 
                            'redirect_url': redirect_url
                            })
                        
            elif(updated_db_user_input.database_type == 'nucl'):
                alignment_user_in = save_specific_alignment_update(updated_db,
                    obj)
                
                if isinstance(alignment_user_in, str): 
                    messages.error(request, str(alignment_user_in))
                    redirect_url = reverse('blastresultuser')
                    return JsonResponse({'success': True, 
                        'redirect_url': redirect_url})

                else:
                    if(BlastnUserInput.objects.filter(
                        output_filename=alignment_user_in.output_filename)
                        .exists()):
                        # Initialize Celery task
                        blastn_update_task.delay(
                            updated_db.slug,
                            alignment_user_in.output_filename,
                            True,
                            request.user.username
                        )

                        messages.info(request, (
                            f"Updating the selected alignment using updated" 
                            f" (child) BLAST database. "
                            f"When the processing is finished, "
                            f"the result will appear in "
                            f"the table. "
                        ))

                        # Redirect user to all task list to view the progress
                        redirect_url = reverse('task_list')
                        return JsonResponse({
                            'success': True, 
                            'redirect_url': redirect_url
                            })

                    elif(tBlastxUserInput.objects.filter(
                        output_filename=alignment_user_in.output_filename)
                        .exists()):
                        # Initialize Celery task
                        tblastx_update_task.delay(
                            updated_db.slug,
                            alignment_user_in.output_filename,
                            True,
                            request.user.username
                        )

                        messages.info(request, (
                            f"Updating the selected alignment using updated" 
                            f" (child) BLAST database. "
                            f"When the processing is finished, "
                            f"the result will appear in "
                            f"the table. "
                        ))

                        # Redirect user to all task list to view the progress
                        redirect_url = reverse('task_list')
                        return JsonResponse({
                            'success': True, 
                            'redirect_url': redirect_url
                            })

                    elif(tBlastnUserInput.objects.filter(
                        output_filename=alignment_user_in.output_filename)
                        .exists()):

                        # Initialize Celery task
                        tblastn_update_task.delay(
                            updated_db.slug,
                            alignment_user_in.output_filename,
                            True,
                            request.user.username
                        )

                        messages.info(request, (
                            f"Updating the selected alignment using updated" 
                            f" (child) BLAST database. "
                            f"When the processing is finished, "
                            f"the result will appear in "
                            f"the table. "
                        ))

                        # Redirect user to all task list to view the progress
                        redirect_url = reverse('task_list')
                        return JsonResponse({
                            'success': True, 
                            'redirect_url': redirect_url
                            })

    context = {
        'obj': obj,
        'to_align_blastp': to_align_blastp,
        'to_align_blastn': to_align_blastn,
        'to_align_blastx': to_align_blastx,
        'to_align_tblastn': to_align_tblastn,
        'to_align_tblastx': to_align_tblastx,
        'slug': slug
    }

    return render(request, "blast_db_creator/update_alignment.html", context)


@login_required(login_url='login')
def update_blast_db(request, slug=None):
    try:
        obj = BlastDBData.objects.get(slug=slug)
    except BlastDBData.MultipleObjectsReturned:
        obj = BlastDBData.objects.filter(slug=slug).first()
    except BlastDBData.DoesNotExist:
        raise Http404
    except:
        raise Http404

    logger.info(
        f"Starting to update the BLAST database."
    )

    successful = 0
    if request.method == 'POST':
        form = UpdateBlastDBForm(request.POST, request.FILES)
        if form.is_valid():
            # Retrieve true or false telling if alignments needs to be updated
            update_alignments = form.cleaned_data['update_alignments']

            if update_alignments:
                # Figure out if any alignments needs to be
                # updated from father_db
                new_db_name = ""
                # Create BLAST Database (child_db)
                if(form.cleaned_data['updated_file_input']):
                    form.save()

                    logger.info(
                        f"Saving user input information for BLAST database "
                        f"update."
                    )

                    if(UpdateBlastDB.objects \
                        .filter(id=form.instance.id).exists()):
                        updating_obj = UpdateBlastDB.objects \
                            .filter(id=form.instance.id).first()
                        in_file = updating_obj.updated_file_input


                        # Create a new object with fathers arguments
                        child_user_input = save_blastdb_update(obj, in_file)

                        # Check BLAST db name
                        if(len(obj.user_input.name_of_blast_db) > 100 - 7 or
                            len(obj.user_input.name_of_blast_db) == 100):
                            messages.error(request, "Cannot update" +
                            " BLAST database: " + F"\"{obj.slug}\""
                            + ". Database name is too long, so no updates " +
                            "are available for this BLAST database.")
                            # Removing created object
                            child_user_input.delete()
                            # Redirecting
                            return redirect('privatedb')

                        else:
                            # Saving user_input object in UpdateBlastDB model
                            #  obj
                            # form.instance.user_input = child_user_input
                            if(UpdateBlastDB.objects \
                            .filter(id=form.instance.id).exists()):
                                update_object = UpdateBlastDB.objects. \
                                filter(id=form.instance.id).update(
                                    user_input = child_user_input
                                )

                            new_db_name = str(child_user_input.name_of_blast_db)


                # If user provided pasted input file
                elif(form.cleaned_data['updated_file_text']):
                    # Retrieving updated_file_text value
                    text = form.cleaned_data['updated_file_text']
                    # Saving text to file 
                    new_file = update_with_text(text, obj.slug)
                    if(new_file):
                        # Create a new object with fathers arguments
                        child_user_input = save_blastdb_update(obj, new_file)
                        # Check BLAST db name
                        if(len(obj.user_input.name_of_blast_db) > 100 - 7 or
                        len(obj.user_input.name_of_blast_db) == 100):
                            messages.error(request, "Cannot update" +
                            " BLAST database: " + F"\"{obj.slug}\""
                            + ". Database name is too long, so no updates " +
                            "are available for this BLAST database.")
                            # Removing created object
                            child_user_input.delete()
                            # Redirecting
                            return redirect('privatedb')

                        else: 
                            # Saving child user_input object in UpdateBlastDB
                            # model obj as foreign key
                            form.instance.user_input = child_user_input
                            # Saving as file
                            form.instance.updated_file_text = ""
                            form.instance.updated_file_input = new_file
                            form.save()

                            new_db_name = str(
                                child_user_input.name_of_blast_db
                            )

                if(obj.user_input.database_type == 'prot'):
                    blastp_alignments = []
                    blastx_alignments = []

                    if(BlastpUserInput.objects.
                        filter(database=obj).exists()):
                        blastp_alignments = BlastpUserInput.objects. \
                        filter(database=obj)
                    
                    if(BlastxUserInput.objects.
                        filter(database=obj).exists()):
                        blastx_alignments = BlastxUserInput.objects. \
                        filter(database=obj)

                            
                    if(not blastp_alignments and not blastx_alignments):
                        # No alignments need to be processed
                        result = createdb_update_task.delay(
                            new_db_name,
                            str(obj.slug),
                            request.user.username
                        )

                        messages.info(request, (
                            f"Updating the \"{obj.slug}\" BLAST database. "
                            f"This BLAST database does not have any "
                            f"alignments to update, so process of updating "
                            f"the alignments was skipped."
                            f" When the processing is finished, "
                            f"the result will appear in "
                            f"the table. "
                        ))

                        return redirect('task_list')

                    elif(blastp_alignments and blastx_alignments):
                        # Process blastp and blastx
                        align_blastp = []
                        align_blastx = []
                        not_suitable_blastp = 0
                        not_suitable_blastx = 0

                        for alignment in blastp_alignments:
                            if(BlastpUserInput.objects \
                                .filter(output_filename=
                                alignment.output_filename).exists()):
                                if(len(alignment.output_filename) == 100 
                                or len(alignment.output_filename) > 100 - 4):
                                    not_suitable_blastp += 1
                                    continue
                                else:
                                    align_blastp.append(
                                        alignment.output_filename
                                    )

                        for alignment in blastx_alignments:
                            if(BlastxUserInput.objects \
                                .filter(output_filename=
                                alignment.output_filename).exists()):
                                if(len(alignment.output_filename) == 100 
                                or len(alignment.output_filename) > 100 - 4):
                                    not_suitable_blastx += 1
                                    continue
                                else:
                                    align_blastx.append(
                                        alignment.output_filename
                                    )

                        result = chain(createdb_update_task.si(
                            name=new_db_name,
                            father_db=obj.slug,
                            user_id=request.user.username) | 
                            group(update_blastp_alignments.si(
                                alignments=align_blastp,
                                name=new_db_name,
                                user_id=request.user.username), 
                                update_blastx_alignments.si(
                                    alignments=align_blastx,
                                    name=new_db_name,
                                    user_id=request.user.username
                                ))).delay()

                        if(not_suitable_blastp > 0 or not_suitable_blastx > 0):
                            messages.info(request, (
                                f"Updating the \"{obj.slug}\" BLAST database. "
                                f"Also updating those BLASTx and BLASTp "
                                f"alignments that "
                                f"can be updated: alignments with output "
                                f"filename which contain 100 characters cannot"
                                f" be updated."
                                f" When the processing is finished, "
                                f"the result will appear in "
                                f"the table."
                            ))
                        else:
                            messages.info(request, (
                                f"Updating the \"{obj.slug}\" BLAST database "
                                f"and it's BLASTx and BLASTp alignments."
                                f" When the processing is finished, "
                                f"the result will appear in "
                                f"the table. "
                            ))

                        return redirect('task_list')

                    elif blastp_alignments:
                        # Process only blastp
                        align = []
                        not_suitable = 0
                        for alignment in blastp_alignments:
                            if(BlastpUserInput.objects \
                                .filter(output_filename=
                                alignment.output_filename).exists()):
                                if(len(alignment.output_filename) == 100 
                                or len(alignment.output_filename) > 100 - 4):
                                    not_suitable += 1
                                    continue
                                else:
                                    align.append(alignment.output_filename)

                        result = chain(
                            createdb_update_task.si(
                                name=new_db_name, 
                                father_db=obj.slug,
                                user_id=request.user.username),
                            update_blastp_alignments.si(
                                alignments=align, 
                                name=new_db_name,
                                user_id=request.user.username)
                        ).delay()

                        if(not_suitable > 0):
                            messages.info(request, (
                                f"Updating the \"{obj.slug}\" BLAST database. "
                                f"Also updating those BLASTp alignments that "
                                f"can be updated: alignments with output "
                                f"filename which contain 100 characters cannot "
                                f"be updated."
                                f" When the processing is finished, "
                                f"the result will appear in "
                                f"the table. "
                            ))
                        else:
                            messages.info(request, (
                                f"Updating the \"{obj.slug}\" BLAST database "
                                f"and it's BLASTp alignments."
                                f" When the processing is finished, "
                                f"the result will appear in "
                                f"the table. "
                            ))

                        return redirect('task_list')
                       
                    elif blastx_alignments:
                        # Process only blastx
                        align = []
                        not_suitable = 0
                        for alignment in blastx_alignments:
                            if(BlastxUserInput.objects \
                                .filter(output_filename=
                                alignment.output_filename).exists()):
                                if(len(alignment.output_filename) == 100 
                                or len(alignment.output_filename) > 100 - 4):
                                    not_suitable += 1
                                    continue
                                else:
                                    align.append(alignment.output_filename)

                        result = chain(
                            createdb_update_task.si(
                                name=new_db_name, 
                                father_db=obj.slug,
                                user_id=request.user.username),
                            update_blastx_alignments.si(
                                alignments=align, 
                                name=new_db_name,
                                user_id=request.user.username)
                        ).delay()

                        if(not_suitable > 0):
                            messages.info(request, (
                                f"Updating the \"{obj.slug}\" BLAST database. "
                                f"Also updating those BLASTx alignments that "
                                f"can be updated: alignments with output "
                                f"filename which contain 100 characters cannot "
                                f"be updated."
                                f" When the processing is finished, "
                                f"the result will appear in "
                                f"the table. "
                            ))
                        else:
                            messages.info(request, (
                                f"Updating the \"{obj.slug}\" BLAST database "
                                f"and it's BLASTx alignments."
                                f" When the processing is finished, "
                                f"the result will appear in "
                                f"the table. "
                            ))

                        return redirect('task_list')


                elif(obj.user_input.database_type == 'nucl'):
                    blastn_alignments = []
                    tblastx_alignments = []
                    tblastn_alignments = []

                    if(BlastnUserInput.objects.
                        filter(database=obj).exists()):
                        blastn_alignments = BlastnUserInput.objects. \
                        filter(database=obj)
                    
                    if(tBlastxUserInput.objects.
                        filter(database=obj).exists()):
                        tblastx_alignments = tBlastxUserInput.objects. \
                        filter(database=obj)

                    if(tBlastnUserInput.objects.
                        filter(database=obj).exists()):
                        tblastn_alignments = tBlastnUserInput.objects. \
                        filter(database=obj)

                    if(not blastn_alignments and not tblastx_alignments 
                        and not tblastn_alignments):
                        # No alignments need to be processed
                        result = createdb_update_task.delay(
                            new_db_name,
                            str(obj.slug),
                            request.user.username
                        )

                        messages.info(request, (
                            f"Updating the \"{obj.slug}\" BLAST database. "
                            f"This BLAST database does not have any "
                            f"alignments to update, so process of updating "
                            f"the alignments was skipped."
                            f" When the processing is finished, "
                            f"the result will appear in "
                            f"the table. "
                        ))

                        return redirect('task_list')

                    elif(blastn_alignments and tblastx_alignments 
                        and tblastn_alignments):
                        # Process blastn and tblastx and tblastn
                        align_blastn = []
                        align_tblastx = []
                        align_tblastn = []
                        not_suitable_blastn = 0
                        not_suitable_tblastx = 0
                        not_suitable_tblastn = 0

                        for alignment in blastn_alignments:
                            if(BlastnUserInput.objects \
                                .filter(output_filename=
                                alignment.output_filename).exists()):
                                if(len(alignment.output_filename) == 100 
                                or len(alignment.output_filename) > 100 - 4):
                                    not_suitable_blastn += 1
                                    continue
                                else:
                                    align_blastn.append(
                                        alignment.output_filename)

                        for alignment in tblastx_alignments:
                            if(tBlastxUserInput.objects \
                                .filter(output_filename=
                                alignment.output_filename).exists()):
                                if(len(alignment.output_filename) == 100 
                                or len(alignment.output_filename) > 100 - 4):
                                    not_suitable_tblastx += 1
                                    continue
                                else:
                                    align_tblastx.append(
                                        alignment.output_filename)

                        for alignment in tblastn_alignments:
                            if(tBlastnUserInput.objects \
                                .filter(output_filename=
                                alignment.output_filename).exists()):
                                if(len(alignment.output_filename) == 100 
                                or len(alignment.output_filename) > 100 - 4):
                                    not_suitable_tblastn += 1
                                    continue
                                else:
                                    align_tblastn.append(
                                        alignment.output_filename)

                        result = chain(createdb_update_task.si(
                            name=new_db_name,
                            father_db=obj.slug,
                            user_id=request.user.username) | 
                            group(
                                update_blastn_alignments.si(
                                    alignments=align_blastn,
                                    name=new_db_name,
                                    user_id=request.user.username), 
                                update_tblastn_alignments.si(
                                    alignments=align_tblastn,
                                    name=new_db_name,
                                    user_id=request.user.username),
                                update_tblastx_alignments.si(
                                    alignments=align_tblastx,
                                    name=new_db_name,
                                    user_id=request.user.username)
                                    )
                                ).delay()
                        
                        if(not_suitable_blastn > 0 or not_suitable_tblastx > 0
                            or not_suitable_tblastn > 0):
                            messages.info(request, (
                                f"Updating the \"{obj.slug}\" BLAST database. "
                                f"Also updating those BLASTn, tBLASTx and "
                                f"tBLASTn alignments that "
                                f"can be updated: alignments with output "
                                f"filename which contain 100 characters cannot "
                                f"be updated."
                                f" When the processing is finished, "
                                f"the result will appear in "
                                f"the table. "
                            ))
                        else:
                            messages.info(request, (
                                f"Updating the \"{obj.slug}\" BLAST database "
                                f"and it's BLASTn, tBLASTx and tBLASTn "
                                f"alignments."
                                f" When the processing is finished, "
                                f"the result will appear in "
                                f"the table. "
                            ))

                        return redirect('task_list')

                    elif(blastn_alignments and tblastx_alignments):
                        align_blastn = []
                        align_tblastx = []
                        not_suitable_tblastx = 0
                        not_suitable_blastn = 0

                        for alignment in blastn_alignments:
                            if(BlastnUserInput.objects \
                                .filter(output_filename=
                                alignment.output_filename).exists()):
                                if(len(alignment.output_filename) == 100 
                                or len(alignment.output_filename) > 100 - 4):
                                    not_suitable_blastn += 1
                                    continue
                                else:
                                    align_blastn.append(
                                        alignment.output_filename)

                        for alignment in tblastx_alignments:
                            if(tBlastxUserInput.objects \
                                .filter(output_filename=
                                alignment.output_filename).exists()):
                                if(len(alignment.output_filename) == 100 
                                or len(alignment.output_filename) > 100 - 4):
                                    not_suitable_tblastx += 1
                                    continue
                                else:
                                    align_tblastx.append(
                                        alignment.output_filename)

                        result = chain(createdb_update_task.si(
                            name=new_db_name,
                            father_db=obj.slug,
                            user_id=request.user.username) | 
                            group(
                                update_blastn_alignments.si(
                                    alignments=align_blastn,
                                    name=new_db_name,
                                    user_id=request.user.username), 
                                update_tblastx_alignments.si(
                                    alignments=align_tblastx,
                                    name=new_db_name,
                                    user_id=request.user.username)
                                    )).delay()

                        if(not_suitable_blastn > 0 or not_suitable_tblastx > 0
                            ):
                            messages.info(request, (
                                f"Updating the \"{obj.slug}\" BLAST database. "
                                f"Also updating those BLASTn, tBLASTx "
                                f"alignments that "
                                f"can be updated: alignments with output "
                                f"filename which contain 100 characters cannot "
                                f"be updated."
                                f" When the processing is finished, "
                                f"the result will appear in "
                                f"the table. "
                            ))
                        else:
                            messages.info(request, (
                                f"Updating the \"{obj.slug}\" BLAST database "
                                f"and it's BLASTn, tBLASTx "
                                f"alignments."
                                f" When the processing is finished, "
                                f"the result will appear in "
                                f"the table. "
                            ))
                        return redirect('task_list')

                    elif(blastn_alignments and tblastn_alignments):
                        align_blastn = []
                        align_tblastn = []
                        not_suitable_blastn = 0
                        not_suitable_tblastn = 0

                        for alignment in blastn_alignments:
                            if(BlastnUserInput.objects \
                                .filter(output_filename=
                                alignment.output_filename).exists()):
                                if(len(alignment.output_filename) == 100 
                                or len(alignment.output_filename) > 100 - 4):
                                    not_suitable_blastn += 1
                                    continue
                                else:
                                    align_blastn.append(
                                        alignment.output_filename)

                        for alignment in tblastn_alignments:
                            if(tBlastnUserInput.objects \
                                .filter(output_filename=
                                alignment.output_filename).exists()):
                                if(len(alignment.output_filename) == 100 
                                or len(alignment.output_filename) > 100 - 4):
                                    not_suitable_tblastn += 1
                                    continue
                                else:
                                    align_tblastn.append(
                                        alignment.output_filename)

                        result = chain(createdb_update_task.si(
                            name=new_db_name,
                            father_db=obj.slug,
                            user_id=request.user.username) | 
                            group(
                                update_blastn_alignments.si(
                                    alignments=align_blastn,
                                    name=new_db_name,
                                    user_id=request.user.username), 
                                update_tblastn_alignments.si(
                                    alignments=align_tblastn,
                                    name=new_db_name,
                                    user_id=request.user.username),
                                )).delay()

                        if(not_suitable_blastn > 0 or not_suitable_tblastn > 0):
                            messages.info(request, (
                                f"Updating the \"{obj.slug}\" BLAST database. "
                                f"Also updating those BLASTn and "
                                f"tBLASTn alignments that "
                                f"can be updated: alignments with output "
                                f"filename which contain 100 characters cannot "
                                f"be updated."
                                f" When the processing is finished, "
                                f"the result will appear in "
                                f"the table. "
                            ))
                        else:
                            messages.info(request, (
                                f"Updating the \"{obj.slug}\" BLAST database "
                                f"and it's BLASTn and tBLASTn "
                                f"alignments."
                                f" When the processing is finished, "
                                f"the result will appear in "
                                f"the table. "
                            ))
                        return redirect('task_list')
                        
                    elif(tblastx_alignments and tblastn_alignments):
                        align_tblastx = []
                        align_tblastn = []
                        not_suitable_tblastx = 0
                        not_suitable_tblastn = 0

                        for alignment in tblastx_alignments:
                            if(tBlastxUserInput.objects \
                                .filter(output_filename=
                                alignment.output_filename).exists()):
                                if(len(alignment.output_filename) == 100 
                                or len(alignment.output_filename) > 100 - 4):
                                    not_suitable_tblastx += 1
                                    continue
                                else:
                                    align_tblastx.append(
                                        alignment.output_filename)

                        for alignment in tblastn_alignments:
                            if(tBlastnUserInput.objects \
                                .filter(output_filename=
                                alignment.output_filename).exists()):
                                if(len(alignment.output_filename) == 100 
                                or len(alignment.output_filename) > 100 - 4):
                                    not_suitable_tblastn += 1
                                    continue
                                else:
                                    align_tblastn.append(
                                        alignment.output_filename)

                        result = chain(createdb_update_task.si(
                            name=new_db_name,
                            father_db=obj.slug,
                            user_id=request.user.username) | 
                            group(
                                update_tblastn_alignments.si(
                                    alignments=align_tblastn,
                                    name=new_db_name,
                                    user_id=request.user.username),
                                update_tblastx_alignments.si(
                                    alignments=align_tblastx,
                                    name=new_db_name,
                                    user_id=request.user.username)
                                    )).delay()

                        if(not_suitable_tblastx > 0
                            or not_suitable_tblastn > 0):
                            messages.info(request, (
                                f"Updating the \"{obj.slug}\" BLAST database. "
                                f"Also updating those tBLASTx and "
                                f"tBLASTn alignments that "
                                f"can be updated: alignments with output "
                                f"filename which contain 100 characters cannot "
                                f"be updated."
                                f" When the processing is finished, "
                                f"the result will appear in "
                                f"the table. "
                            ))
                        else:
                            messages.info(request, (
                                f"Updating the \"{obj.slug}\" BLAST database "
                                f"and it's tBLASTx and tBLASTn "
                                f"alignments."
                                f" When the processing is finished, "
                                f"the result will appear in "
                                f"the table. "
                            ))
                        return redirect('task_list')

                    elif blastn_alignments:
                        # Process only blastn
                        align = []
                        not_suitable = 0
                        for alignment in blastn_alignments:
                            if(BlastnUserInput.objects \
                                .filter(output_filename=
                                alignment.output_filename).exists()):
                                if(len(alignment.output_filename) == 100 
                                or len(alignment.output_filename) > 100 - 4):
                                    not_suitable += 1
                                    continue
                                else:
                                    align.append(alignment.output_filename)

                        result = chain(
                            createdb_update_task.si(
                                name=new_db_name, 
                                father_db=obj.slug,
                                user_id=request.user.username),
                            update_blastn_alignments.si(
                                alignments=align, 
                                name=new_db_name,
                                user_id=request.user.username)
                        ).delay()

                        if(not_suitable > 0):
                            messages.info(request, (
                                f"Updating the \"{obj.slug}\" BLAST database. "
                                f"Also updating those BLASTn alignments that "
                                f"can be updated: alignments with output "
                                f"filename which contain 100 characters cannot "
                                f"be updated."
                                f" When the processing is finished, "
                                f"the result will appear in "
                                f"the table. "
                            ))
                        else:
                            messages.info(request, (
                                f"Updating the \"{obj.slug}\" BLAST database "
                                f"and it's BLASTn alignments."
                                f" When the processing is finished, "
                                f"the result will appear in "
                                f"the table. "
                            ))

                        return redirect('task_list')

                    elif tblastx_alignments:
                        # Process only tblastx
                        align = []
                        not_suitable = 0
                        for alignment in tblastx_alignments:
                            if(tBlastxUserInput.objects \
                                .filter(output_filename=
                                alignment.output_filename).exists()):
                                if(len(alignment.output_filename) == 100 
                                or len(alignment.output_filename) > 100 - 4):
                                    not_suitable += 1
                                    continue
                                else:
                                    align.append(alignment.output_filename)

                        result = chain(
                            createdb_update_task.si(
                                name=new_db_name, 
                                father_db=obj.slug,
                                user_id=request.user.username),
                            update_tblastx_alignments.si(
                                alignments=align, 
                                name=new_db_name,
                                user_id=request.user.username)
                        ).delay()

                        if(not_suitable > 0):
                            messages.info(request, (
                                f"Updating the \"{obj.slug}\" BLAST database. "
                                f"Also updating those tBLASTx alignments that "
                                f"can be updated: alignments with output "
                                f"filename which contain 100 characters cannot "
                                f"be updated."
                                f" When the processing is finished, "
                                f"the result will appear in "
                                f"the table. "
                            ))
                        else:
                            messages.info(request, (
                                f"Updating the \"{obj.slug}\" BLAST database "
                                f"and it's tBLASTx alignments."
                                f" When the processing is finished, "
                                f"the result will appear in "
                                f"the table. "
                            ))

                        return redirect('task_list')

                    elif tblastn_alignments:
                        # Process only tblastn
                        align = []
                        not_suitable = 0
                        for alignment in tblastn_alignments:
                            if(tBlastnUserInput.objects \
                                .filter(output_filename=
                                alignment.output_filename).exists()):
                                if(len(alignment.output_filename) == 100 
                                or len(alignment.output_filename) > 100 - 4):
                                    not_suitable += 1
                                    continue
                                else:
                                    align.append(alignment.output_filename)

                        result = chain(
                            createdb_update_task.si(
                                name=new_db_name, 
                                father_db=obj.slug,
                                user_id=request.user.username),
                            update_tblastn_alignments.si(
                                alignments=align, 
                                name=new_db_name,
                                user_id=request.user.username)
                        ).delay()

                        if(not_suitable > 0):
                            messages.info(request, (
                                f"Updating the \"{obj.slug}\" BLAST database. "
                                f"Also updating those tBLASTn alignments that "
                                f"can be updated: alignments with output "
                                f"filename which contain 100 characters cannot "
                                f"be updated."
                                f" When the processing is finished, "
                                f"the result will appear in "
                                f"the table. "
                            ))
                        else:
                            messages.info(request, (
                                f"Updating the \"{obj.slug}\" BLAST database "
                                f"and it's tBLASTn alignments."
                                f" When the processing is finished, "
                                f"the result will appear in "
                                f"the table. "
                            ))

                        return redirect('task_list')


            elif update_alignments == False:
                # Only create BLAST database using Celery task
                if(form.cleaned_data['updated_file_input']):
                    form.save()

                    if(UpdateBlastDB.objects \
                        .filter(id=form.instance.id).exists()):
                        updating_obj = UpdateBlastDB.objects \
                            .filter(id=form.instance.id).first()
                        in_file = updating_obj.updated_file_input

                        # Create a new object with fathers arguments
                        child_user_input = save_blastdb_update(obj, in_file)

                        # Check BLAST db name
                        if(len(obj.user_input.name_of_blast_db) > 100 - 7 or
                            len(obj.user_input.name_of_blast_db) == 100):
                            messages.error(request, "Cannot update" +
                            " BLAST database: " + F"\"{obj.slug}\""
                            + ". Database name is too long, so no updates " +
                            "are available for this BLAST database.")
                            # Removing created object
                            child_user_input.delete()
                            # Redirecting
                            return redirect('privatedb')

                        else:
                            # Saving user_input object in UpdateBlastDB model
                            #  obj
                            if(UpdateBlastDB.objects \
                            .filter(id=form.instance.id).exists()):
                                update_object = UpdateBlastDB.objects. \
                                filter(id=form.instance.id).update(
                                    user_input = child_user_input
                                )
                            
                            # Reload BLAST database by initializing Celery task
                            createdb_update_task.delay(
                                child_user_input.name_of_blast_db, 
                                str(obj.slug),
                                request.user.username
                            )

                            messages.info(request, (
                                f"Updating the"
                                f" \"{child_user_input.name_of_blast_db}\" "
                                f"BLAST database. "
                                f"When the processing is finished, "
                                f"the result will appear in "
                                f"the table. "
                            ))

                            # Redirect user to all task list to view the 
                            # progress
                            return redirect('task_list')

                # If user provided pasted input file
                elif(form.cleaned_data['updated_file_text']):
                    # Retrieving updated_file_text value
                    text = form.cleaned_data['updated_file_text']
                    # Saving text to file 
                    new_file = update_with_text(text, obj.slug)
                    if(new_file):
                        # Create a new object with fathers arguments
                        child_user_input = save_blastdb_update(obj, new_file)
                        # Check BLAST db name
                        if(len(obj.user_input.name_of_blast_db) > 100 - 7 or
                        len(obj.user_input.name_of_blast_db) == 100):
                            messages.error(request, "Cannot update" +
                            " BLAST database: " + F"\"{obj.slug}\""
                            + ". Database name is too long, so no updates " +
                            "are available for this BLAST database.")
                            # Removing created object
                            child_user_input.delete()
                            # Redirecting
                            return redirect('privatedb')

                        else: 
                            # Saving child user_input object in UpdateBlastDB
                            # model obj as foreign key
                            form.instance.user_input = child_user_input
                            # Saving as file
                            form.instance.updated_file_text = ""
                            form.instance.updated_file_input = new_file
                            form.save()


                            # Reload BLAST database by initializing Celery task
                            createdb_update_task.delay(
                                child_user_input.name_of_blast_db, 
                                str(obj.slug),
                                request.user.username
                            )

                            messages.info(request, (
                                f"Updating the"
                                f" \"{child_user_input.name_of_blast_db}\" "
                                f"BLAST database. "
                                f"When the processing is finished, "
                                f"the result will appear in "
                                f"the table. "
                            ))

                            # Redirect user to all task list to view 
                            # the progress
                            return redirect('task_list')

        else:
            context = {
                'object': obj,
                'updateform': form,
                'slug': slug
            }

            return render(request, 
                "blast_db_creator/update_db.html", context)

    else:
        form = UpdateBlastDBForm()

    context = {
        'object': obj,
        'updateform': form,
        'slug': slug
    }

    return render(request, "blast_db_creator/update_db.html", context)


def retrieve_and_generate_tree(request):
    if request.method == 'POST':
        generate_tree_for = request.POST.get('generate_tree_for')

        if(BlastDBData.objects.filter(slug=generate_tree_for).exists()):
            father_db = BlastDBData.objects.filter(slug=generate_tree_for) \
                .first()
            return JsonResponse({'slug': father_db.slug})

@login_required(login_url='login')
def family_tree(request, slug=None):
    # View for generating family tree for specific BLAST database
    if request.user.is_authenticated:
        username = request.user.username
        if(BlastDBData.objects.filter(slug=slug).exists()):
            father_db = BlastDBData.objects.filter(slug=slug).first()
            father_db_input = UserInput.objects \
                .filter(name_of_blast_db=slug).first()
            db_type = father_db_input.database_type

            # Use recursion to build a tree 
            def generate_tree(father_db):
                db_tree = {'father' : father_db.slug, 'children' : []}
                children = BlastDBData.objects.exclude(father_database=None) \
                    .filter(user_input__database_type=db_type) \
                    .filter(user_input__user__username=username) \
                    .filter(father_database__slug=father_db.slug)
                for c in children:
                    db_tree['children'].append(generate_tree(c))
                return db_tree
            
            db_tree = generate_tree(father_db)

            logger.info(
                f"Generating hierarchical tree diagram for specific "
                f"BLAST database."
            )
        
            context = {
                'father_db': father_db.slug,
                'db_tree': db_tree,
            }
        else:
            window.alert("Something went wrong." +
                " Could not find selected BLAST database")
            return redirect('privatedb')

    else:
        messages.error(request, "Private databases " +
            "available for logged in users only.")
        return redirect('login')

    return render(request, "blast_db_creator/generate_tree.html", context)


def retrieve_alignments_multi(objects, alignments, index):
    # Function for batch alignments
    if alignments:
        alignments_arr = []
        for db in objects:
            for alignment in alignments:
                if(db.id == alignment.batch_align.id):
                    alignments_arr.append(alignment)
        return alignments_arr
    else:
        return None

def retrieve_multi_file_content(alignments, model_name, blast_request, result):
    # Retrieving file content results for each alignments results in 
    # batch
    alignment_content = {}    
    for align in alignments:
        blast_out = model_name.objects \
            .filter(**{blast_request: align}).first()
        if blast_out:
            if os.path.exists('media/' + str(getattr(blast_out, result))):
                    file = open('media/' + str(getattr(blast_out, result)), 'r')
                    file_content = file.read()
                    file.close()
                    all_chunks = split_file_to_chunks(file_content)
                    if all_chunks:
                        alignment_content[align.database.slug] = all_chunks
                    else:
                        alignment_content[align.database.slug] = \
                            "Results are not found. Please try again."
            else:
                alignment_content[align.database.slug] = \
                    "Results are not found. Please try again."
    return alignment_content
    
@login_required(login_url='login')
def batch_alignment(request, slug=False):
    # Sending data such as task, date, query_file, db_name and output filename
    generated_objects = []
    index_of_multi = ""
    if(BatchAlign.objects.filter(unique_db_index=slug).exists()):
        generated_objects = BatchAlign.objects.filter(unique_db_index=slug)
        index_of_multi = generated_objects[0].unique_db_index

    # Get all multi alignments
    retrieve_blastp_align = BlastpUserInput.objects.exclude(batch_align=None)
    retrieve_blastx_align = BlastxUserInput.objects.exclude(batch_align=None)
    retrieve_tblastx_align = tBlastxUserInput.objects.exclude(batch_align=None)
    retrieve_tblastn_align = tBlastnUserInput.objects.exclude(batch_align=None)
    retrieve_blastn_align = BlastnUserInput.objects.exclude(batch_align=None)

    # Get array of suitable alignments, only one of them is not None
    blastp_alignments = retrieve_alignments_multi(
        generated_objects, 
        retrieve_blastp_align, index_of_multi)
    blastx_alignments = retrieve_alignments_multi(
        generated_objects, 
        retrieve_blastx_align, index_of_multi)
    blastn_alignments = retrieve_alignments_multi(
        generated_objects, 
        retrieve_blastn_align, index_of_multi)
    tblastx_alignments = retrieve_alignments_multi(
        generated_objects, 
        retrieve_tblastx_align, index_of_multi)
    tblastn_alignments = retrieve_alignments_multi(
        generated_objects, 
        retrieve_tblastn_align, index_of_multi)

    logger.info(
        f"Retrieving alignments results content."
    )

    alignment_content = {}
    if(blastp_alignments):
        alignment_content = retrieve_multi_file_content(
            blastp_alignments, 
            BlastpResults, 
            "blastp_request", 
            "blastp_result"
        )
    elif(blastx_alignments):
        alignment_content = retrieve_multi_file_content(
            blastx_alignments, 
            BlastxResults, 
            "blastx_request", 
            "blastx_result"
        )
    elif(blastn_alignments):
        alignment_content = retrieve_multi_file_content(
            blastn_alignments, 
            BlastnResults, 
            "blastn_request", 
            "blastn_result"
        )
    elif(tblastx_alignments):
        alignment_content = retrieve_multi_file_content(
            tblastx_alignments, 
            tBlastxResults, 
            "tblastx_request", 
            "tblastx_result"
        )
    elif(tblastn_alignments):
        alignment_content = retrieve_multi_file_content(
            tblastn_alignments, 
            tBlastnResults, 
            "tblastn_request", 
            "tblastn_result"
        )

    context = {
        'index_of_multi': index_of_multi,
        'databases': generated_objects,
        'blastp_alignments': blastp_alignments,
        'blastx_alignments': blastx_alignments,
        'blastn_alignments': blastn_alignments,
        'tblastx_alignments': tblastx_alignments,
        'tblastn_alignments': tblastn_alignments,
        'alignment_content': alignment_content,
    }

    return render(request, "blast_db_creator/batch_alignment_page.html", context)


def retrieve_multi_dbs_data(request):
    # Checking if the data was retrieved using ajax
    is_ajax = request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest'
    if request.method == 'POST' and is_ajax:
        db_to_align = request.POST.getlist('db_to_align[]')
        if(db_to_align):
            unique_db_index = generate_unique_db_index()
            not_found = []
            for db in db_to_align:
                if(BlastDBData.objects.filter(slug=db).exists()):
                    database_used = BlastDBData.objects.filter(slug=db).first()
                    # Create new object for each database selected
                    new_object = BatchAlign()
                    new_object.unique_db_index = unique_db_index
                    new_object.db_type = database_used.user_input.database_type
                    new_object.database = database_used
                    new_object.user_input = database_used.user_input
                    new_object.save()

                else:
                    not_found.append(db)

            if(not_found):
                messages.info(request, 
                (
                    F"Could not find some selected BLAST databases: "
                    F" \"{', '.join(not_found)}\". "
                    F"Batch alignments still be generated for other BLAST "
                    F"databases."
                ))
            
            if(BatchAlign.objects \
                    .filter(unique_db_index=unique_db_index).exists()):
                return JsonResponse({'slug': unique_db_index})
