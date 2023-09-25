from pickle import FALSE, TRUE
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
from django.contrib import messages
from zipfile import ZipFile
from django.http import JsonResponse
import logging

import subprocess
import os
import re
import string
import random
import json
from django.utils import timezone

logger = logging.getLogger("django")

def remove_database_data(path, name):
    for file_name in os.listdir(path):
        if os.path.isfile(os.path.join(path, file_name)):
            if re.search("^" + name + "\.", file_name):
                os.remove(path + file_name)


def remove_inputs(path, input_file):
    for file_name in os.listdir(path):
        if os.path.isfile(os.path.join(path, file_name)):
            if re.search("^" + os.path.basename(str(input_file)) + "$",
                         file_name):
                os.remove(path + file_name)


def createdb(name, is_update):
    # function which creates BLAST databases using subprocess
    user_input_obj = UserInput.objects.filter(name_of_blast_db=name).first()
    # Adding variables to save the location of files
    if(user_input_obj):
        input_file_loc = 'media/' + str(user_input_obj.input_file)
        taxidmap = 'media/' + str(user_input_obj.taxid_map)
        database_name = user_input_obj.name_of_blast_db
        blast_db_loc = 'media/blast_databases/'

        # Running makeblastdb using subprocess
        create_db = subprocess.run(['makeblastdb',
            '-in', input_file_loc,
            '-dbtype', user_input_obj.database_type,
            '-input_type', user_input_obj.input_type,
            '-out', blast_db_loc + database_name,
            *(['-title', user_input_obj.database_title]
                if user_input_obj.database_title else []),
            *(['-parse_seqids']
                if user_input_obj.parse_seqids else []),
            *(['-hash_index']
                if user_input_obj.hash_index else []),
            *(['-blastdb_version', user_input_obj
                .blastdb_version]
                if user_input_obj.blastdb_version else []),
            *(['-taxid', user_input_obj.taxid]
                if user_input_obj.taxid else []),
            *(['-taxid_map', taxidmap] if
                str(user_input_obj.taxid_map) else [])],
            capture_output=TRUE)

        # If any errors happen from blast+
        if create_db.stderr:
            # Deleting file if mistakes occured
            dir_path = 'media/blast_databases/'
            dir_path_inputs = 'media/users_inputs/'
            dir_path_params = 'media/user_taxid_files/'
            remove_database_data(dir_path, database_name)
            if not is_update:
                remove_inputs(dir_path_inputs, user_input_obj.input_file)
                remove_inputs(dir_path_params, user_input_obj.taxid_map)
            # Checking if any error messages contain full location of files,
            # clearing the location
            create_db_error_message = create_db.stderr.decode("utf-8")
            if(re.search('media\/', create_db_error_message)):
                match = re.search(".+?(?=\/)", create_db_error_message)
                part_one = match.group(0)
                match1 = re.search("([^\/]+$)", create_db_error_message)
                part_two = match1.group(0)
                create_db_error_message = part_one + part_two

            # Checking if error message is about wrong type of database
            # when user uploads protein sequences, but selects
            # nucleotide database type
            is_wrong_type = re.search(
                '(FASTA-Reader: Ignoring invalid residues at position\(s\):)+.+',
                create_db_error_message)
            if(is_wrong_type):
                create_db_error_message = is_wrong_type.group(0) + " ...  "
                create_db_error_message = str(create_db_error_message)[:110] + \
                    " There might be protein sequences in the input file. " + \
                    "Please choose BLAST database type as protein or upload " + \
                    "a new file, containing nucleotide sequences."
            return create_db_error_message[:250] + "..."
        else:
            # if there are no errors
            return None


def saveblastdb_data(name):
    # Saving object in database BlastDBData
    if(UserInput.objects.filter(name_of_blast_db=name).exists()):
        user_input_obj = UserInput.objects.get(name_of_blast_db=name)
        database_name = user_input_obj.name_of_blast_db

        # Zipping output files
        filename = 'media/blast_databases/' + database_name + '.zip'
        directory_path = 'media/blast_databases/'

        # Looping through all files in directory
        # searching for correct ones, adding filenames to list
        correct_filenames = []
        for file_name in os.listdir(directory_path):
            if os.path.isfile(os.path.join(directory_path, file_name)):
                if re.search("^" + database_name + "\.", file_name):
                    correct_filenames.append(file_name)

        # Creating zip file, adding correct files
        database_zip = ZipFile(filename, 'w')
        for file in correct_filenames:
            database_zip.write(directory_path+file, file)
        database_zip.close()

        # Creating new object or updating it
        if(BlastDBData.objects.filter(user_input=database_name).exists()):
            BlastDBData.objects.filter(user_input=database_name) \
                .update(zip_file='blast_databases/' + database_name + '.zip')
        else:
            new_obj = BlastDBData()
            new_obj.user_input = user_input_obj
            new_obj.zip_file.name = 'blast_databases/' + database_name + '.zip'
            new_obj.save()


def run_blastn(database_slug, blastn_form_slug, is_multi):
    # Taking objects from models
    if(BlastDBData.objects.filter(slug=database_slug).exists()):
        database_obj = BlastDBData.objects.get(slug=database_slug)

        user_form_obj = BlastnUserInput.objects.get(
            output_filename=blastn_form_slug)
        
        # Saving database name to find corresponding files
        if(database_obj.user_input):
            database_name = database_obj.user_input.name_of_blast_db

        # Adding variables to save the location of files
        query_file_dir = 'media/' + str(user_form_obj.query_file)
        database_file_dir = 'media/blast_databases/'
        result_output_dir = 'media/blastn_outputs/'

        # Checking if database already exists (when updating)
        for file_name in os.listdir(result_output_dir):
            if os.path.isfile(os.path.join(result_output_dir, file_name)):
                if re.search("^" + database_name + "\.", file_name):
                    remove_inputs(result_output_dir, database_name)

        # Running blastn using subprocess
        running_blastn = subprocess.run(['blastn',
            '-query', query_file_dir,
            '-db', database_file_dir + database_name,
            '-out',  result_output_dir + user_form_obj.output_filename,
            *(['-query_loc', user_form_obj.query_location]
            if user_form_obj.query_location else []),
            *(['-strand', user_form_obj.strand]
                if user_form_obj.strand else []),
            *(['-task', user_form_obj.task]
                if user_form_obj.task else []),
            *(['-evalue', str(user_form_obj.evalue)]
                if user_form_obj.evalue else []),
            *(['-word_size', str(user_form_obj.word_size)]
                if user_form_obj.word_size else []),
            *(['-gapopen', str(user_form_obj.gap_open)]
                if user_form_obj.gap_open else []),
            *(['-gapextend', str(user_form_obj.gap_extend)]
                if user_form_obj.gap_extend else []),
            *(['-reward', str(user_form_obj.reward)]
                if user_form_obj.reward else []),
            *(['-penalty', str(user_form_obj.penalty)]
                if user_form_obj.penalty else []),
            *(['-show_gis']
                if user_form_obj.show_gis else []),
            *(['-line_length', str(user_form_obj.line_length)]
                if user_form_obj.line_length else []),
            *(['-sorthits', user_form_obj.sort_hits]
                if user_form_obj.sort_hits else []),
            *(['-sorthsps', user_form_obj.sort_hsps]
                if user_form_obj.sort_hsps else []),
            *(['-gilist', 'media/' + str(user_form_obj.gilist)]
                if user_form_obj.gilist else []),
            *(['-seqidlist', 'media/' + str(user_form_obj.seqidlist)]
                if user_form_obj.seqidlist else []),
            *(['-negative_gilist', 'media/' + str(user_form_obj.negative_gilist)]
                if user_form_obj.negative_gilist else []),
            *(['-negative_seqidlist',
            'media/' + str(user_form_obj.negative_seqidlist)]
                if user_form_obj.negative_seqidlist else []),
            *(['-taxids', user_form_obj.taxids]
                if user_form_obj.taxids else []),
            *(['-negative_taxids', user_form_obj.negative_taxids]
                if user_form_obj.negative_taxids else []),
            *(['-taxidlist', 'media/' + str(user_form_obj.taxidlist)]
                if user_form_obj.taxidlist else []),
            *(['-negative_taxidlist',
            'media/' + str(user_form_obj.negative_taxidlist)]
                if user_form_obj.negative_taxidlist else []),
            *(['-perc_identity', str(user_form_obj.perc_identity)]
                if user_form_obj.perc_identity else []),
            *(['-qcov_hsp_perc', str(user_form_obj.qcov_hsp_perc)]
                if user_form_obj.qcov_hsp_perc else []),
            *(['-max_hsps', str(user_form_obj.max_hsps)]
                if user_form_obj.max_hsps else []),
            *(['-subject_besthit']
                if user_form_obj.subject_besthit else []),
            *(['-parse_deflines'] if user_form_obj.parse_deflines else []),
            *(['-soft_masking', str(user_form_obj.soft_masking)]
                if user_form_obj.soft_masking else []),
            *(['-lcase_masking']
                if user_form_obj.lcase_masking else []),
            *(['-max_target_seqs', str(user_form_obj.max_target_seqs)]
                if user_form_obj.max_target_seqs else []),
            ],
        capture_output=TRUE)

        # If any problems happend from blastn
        if running_blastn.stderr:
            if hasattr(database_obj, 'father_database'):
                if not(database_obj.father_database):
                    if not is_multi:
                        # Deleting file if mistakes occured and if father database
                        dir_path_input = 'media/blastn_user_inputs/'
                        dir_path_result = 'media/blastn_outputs/'
                        dir_path_params = 'media/blastn_inputs_parameters/'

                        remove_inputs(dir_path_input, user_form_obj.query_file)
                        remove_inputs(dir_path_result, 
                            user_form_obj.output_filename)

                        if(user_form_obj.gilist):
                            param_file_name = str(user_form_obj.gilist)
                            remove_inputs(dir_path_params, param_file_name)
                        elif(user_form_obj.seqidlist):
                            param_file_name = str(user_form_obj.seqidlist)
                            remove_inputs(dir_path_params, param_file_name)
                        elif(user_form_obj.negative_gilist):
                            param_file_name = str(user_form_obj.negative_gilist)
                            remove_inputs(dir_path_params, param_file_name)
                        elif(user_form_obj.negative_seqidlist):
                            param_file_name = str(user_form_obj.negative_seqidlist)
                            remove_inputs(dir_path_params, param_file_name)
                        elif(user_form_obj.taxidlist):
                            param_file_name = str(user_form_obj.taxidlist)
                            remove_inputs(dir_path_params, param_file_name)
                        elif(user_form_obj.negative_taxidlist):
                            param_file_name = str(user_form_obj.negative_taxidlist)
                            remove_inputs(dir_path_params, param_file_name)

            # Checking if error messages contain any file location
            # if file location is provided, removing it from message
            running_blastn_error_msg = running_blastn.stderr.decode("utf-8")
            if(re.search('media\/', running_blastn_error_msg)):
                match = re.search(".+?(?=\/)", running_blastn_error_msg)
                part_one = match.group(0)
                match1 = re.search("([^\/]+$)", running_blastn_error_msg)
                part_two = match1.group(0)
                running_blastn_error_msg = part_one + part_two

            return running_blastn_error_msg[:250] + "..."
        else:
            return None


def saveblastn_result(blastn_form_slug):
    # Saving object data into database BlastnResults
    # or updating it.
    if(BlastnResults.objects.filter(blastn_request=blastn_form_slug).exists()):
        blastn_request = BlastnUserInput.objects.get(
            output_filename=blastn_form_slug)
        BlastnResults.objects.filter(blastn_request=blastn_form_slug) \
            .update(blastn_result='blastn_outputs/' +
                    blastn_request.output_filename)
    else:
        if(BlastnUserInput.objects \
            .filter(output_filename=blastn_form_slug).exists()):
            blastn_request = BlastnUserInput.objects.get(
                output_filename=blastn_form_slug)
            new_obj = BlastnResults()
            new_obj.blastn_request = blastn_request
            new_obj.blastn_result = 'blastn_outputs/' + \
                blastn_request.output_filename
            new_obj.save()


def run_blastp(database_slug, blastp_form_slug, is_multi):
    # Function to run blastp
    if(BlastDBData.objects.filter(slug=database_slug).exists()):
        database_obj = BlastDBData.objects.get(slug=database_slug)

        user_form_obj = BlastpUserInput.objects.get(
            output_filename=blastp_form_slug)
        # Saving database name to find corresponding files
        if(database_obj.user_input):
            database_name = database_obj.user_input.name_of_blast_db

            # Adding variables to save the location of files
            query_file_dir = 'media/' + str(user_form_obj.query_file)
            database_file_dir = 'media/blast_databases/'
            blastp_output_dir = 'media/blastp_outputs/'

            # Checking if database already exists (when updating)
            for file_name in os.listdir(blastp_output_dir):
                if os.path.isfile(os.path.join(blastp_output_dir, file_name)):
                    if re.search("^" + database_name + "\.", file_name):
                        remove_inputs(blastp_output_dir, database_name)

        running_blastp = subprocess.run(['blastp',
            '-query', query_file_dir,
            '-db', database_file_dir + database_name,
            '-out', blastp_output_dir + user_form_obj.output_filename,
            *(['-query_loc', user_form_obj.query_location]
            if user_form_obj.query_location else []),
            *(['-task', user_form_obj.task]
                if user_form_obj.task else []),
            *(['-evalue', str(user_form_obj.evalue)]
                if user_form_obj.evalue else []),
            *(['-word_size', str(user_form_obj.word_size)]
                if user_form_obj.word_size else []),
            *(['-gapopen', str(user_form_obj.gap_open)]
                if user_form_obj.gap_open else []),
            *(['-gapextend', str(user_form_obj.gap_extend)]
                if user_form_obj.gap_extend else []),
            *(['-matrix', user_form_obj.matrix]
                if user_form_obj.matrix else []),
            *(['-threshold', str(user_form_obj.threshold)]
                if user_form_obj.threshold else []),
            *(['-show_gis']
                if user_form_obj.show_gis else []),
            *(['-line_length', str(user_form_obj.line_length)]
                if user_form_obj.line_length else []),
            *(['-sorthits', user_form_obj.sort_hits]
                if user_form_obj.sort_hits else []),
            *(['-sorthsps', user_form_obj.sort_hsps]
                if user_form_obj.sort_hsps else []),
            *(['-gilist', 'media/' + str(user_form_obj.gilist)]
                if user_form_obj.gilist else []),
            *(['-seqidlist', 'media/' + str(user_form_obj.seqidlist)]
                if user_form_obj.seqidlist else []),
            *(['-negative_gilist', 'media/' + str(user_form_obj.negative_gilist)]
                if user_form_obj.negative_gilist else []),
            *(['-negative_seqidlist',
            'media/' + str(user_form_obj.negative_seqidlist)]
                if user_form_obj.negative_seqidlist else []),
            *(['-taxids', user_form_obj.taxids]
                if user_form_obj.taxids else []),
            *(['-negative_taxids', user_form_obj.negative_taxids]
                if user_form_obj.negative_taxids else []),
            *(['-taxidlist', 'media/' + str(user_form_obj.taxidlist)]
                if user_form_obj.taxidlist else []),
            *(['-negative_taxidlist',
            'media/' + str(user_form_obj.negative_taxidlist)]
                if user_form_obj.negative_taxidlist else []),
            *(['-qcov_hsp_perc', str(user_form_obj.qcov_hsp_perc)]
                if user_form_obj.qcov_hsp_perc else []),
            *(['-max_hsps', str(user_form_obj.max_hsps)]
                if user_form_obj.max_hsps else []),
            *(['-subject_besthit']
                if user_form_obj.subject_besthit else []),
            *(['-parse_deflines']
                if user_form_obj.parse_deflines else []),
            *(['-soft_masking', str(user_form_obj.soft_masking)]
                if user_form_obj.soft_masking else []),
            *(['-lcase_masking']
                if user_form_obj.lcase_masking else []),
            *(['-max_target_seqs', str(user_form_obj.max_target_seqs)]
                if user_form_obj.max_target_seqs else []),
            ],
        capture_output=TRUE)

        if running_blastp.stderr:
            if hasattr(database_obj, 'father_database'):
                if not(database_obj.father_database):
                    if not is_multi:
                        # Deleting file if mistakes occured
                        dir_path_input = 'media/blastp_user_inputs/'
                        dir_path_result = 'media/blastp_outputs/'
                        dir_path_params = 'media/blastp_inputs_parameters/'

                        remove_inputs(dir_path_input, user_form_obj.query_file)
                        remove_inputs(dir_path_result, 
                            user_form_obj.output_filename)

                        param_file_name = ""
                        if(user_form_obj.gilist):
                            param_file_name = str(user_form_obj.gilist)
                        elif(user_form_obj.seqidlist):
                            param_file_name = str(user_form_obj.seqidlist)
                        elif(user_form_obj.negative_gilist):
                            param_file_name = str(user_form_obj.negative_gilist)
                        elif(user_form_obj.negative_seqidlist):
                            param_file_name = str(user_form_obj.negative_seqidlist)
                        elif(user_form_obj.taxidlist):
                            param_file_name = str(user_form_obj.taxidlist)
                        elif(user_form_obj.negative_taxidlist):
                            param_file_name = str(user_form_obj.negative_taxidlist)

                        if(param_file_name):
                            remove_inputs(dir_path_params, param_file_name)

            # If any errors happend and it has file location,
            # remove the location from it
            running_blastp_error_msg = running_blastp.stderr.decode("utf-8")
            if(re.search('media\/', running_blastp_error_msg)):
                match = re.search(".+?(?=\/)", running_blastp_error_msg)
                part_one = match.group(0)
                match1 = re.search("([^\/]+$)", running_blastp_error_msg)
                part_two = match1.group(0)
                running_blastp_error_msg = part_one + part_two

            return running_blastp_error_msg[:250] + "..."
        else:
            return None


def saveblastp_result(blastp_form_slug):
    # Creating new object or updating it to BlastpResults
    if(BlastpResults.objects.filter(blastp_request=blastp_form_slug).exists()):
        blastp_request = BlastpUserInput.objects.get(
            output_filename=blastp_form_slug)
        BlastpResults.objects.filter(blastp_request=blastp_form_slug) \
            .update(blastp_result='blastp_outputs/' +
                    blastp_request.output_filename)
    else:
        blastp_request = BlastpUserInput.objects.get(
            output_filename=blastp_form_slug)
        new_obj = BlastpResults()
        new_obj.blastp_request = blastp_request
        new_obj.blastp_result = 'blastp_outputs/' + \
            blastp_request.output_filename
        new_obj.save()


def run_blastx(database_slug, blastx_form_slug, is_multi):
    # Function to run blastx
    if(BlastDBData.objects.filter(slug=database_slug).exists()):
        database_obj = BlastDBData.objects.get(slug=database_slug)

        user_form_obj = BlastxUserInput.objects.get(
            output_filename=blastx_form_slug)
        # Saving database name to find corresponding files
        if(database_obj.user_input):
            database_name = database_obj.user_input.name_of_blast_db

        query_file_dir = 'media/' + str(user_form_obj.query_file)
        database_file_dir = 'media/blast_databases/'
        blastx_output_dir = 'media/blastx_outputs/'

        for file_name in os.listdir(blastx_output_dir):
            if os.path.isfile(os.path.join(blastx_output_dir, file_name)):
                if re.search("^" + database_name + "\.", file_name):
                    remove_inputs(blastx_output_dir, database_name)

        running_blastx = subprocess.run([
            'blastx',
            '-query', query_file_dir,
            '-db', database_file_dir + database_name,
            '-out', blastx_output_dir + user_form_obj.output_filename,
            *(['-query_loc', user_form_obj.query_location]
            if user_form_obj.query_location else []),
            *(['-strand', user_form_obj.strand]
            if user_form_obj.strand else []),
            *(['-task', user_form_obj.task]
            if user_form_obj.task else []),
            *(['-evalue', str(user_form_obj.evalue)]
            if user_form_obj.evalue else []),
            *(['-word_size', str(user_form_obj.word_size)]
            if user_form_obj.word_size else []),
            *(['-gapopen', str(user_form_obj.gap_open)]
            if user_form_obj.gap_open else []),
            *(['-gapextend', str(user_form_obj.gap_extend)]
            if user_form_obj.gap_extend else []),
            *(['-threshold', str(user_form_obj.threshold)]
            if user_form_obj.threshold else []),
            *(['-show_gis']
            if user_form_obj.show_gis else []),
            *(['-line_length', str(user_form_obj.line_length)]
            if user_form_obj.line_length else []),
            *(['-sorthits', user_form_obj.sort_hits]
            if user_form_obj.sort_hits else []),
            *(['-sorthsps', user_form_obj.sort_hsps]
            if user_form_obj.sort_hsps else []),
            *(['-gilist', 'media/' + str(user_form_obj.gilist)]
            if user_form_obj.gilist else []),
            *(['-seqidlist', 'media/' + str(user_form_obj.seqidlist)]
            if user_form_obj.seqidlist else []),
            *(['-negative_gilist', 'media/' + str(user_form_obj.negative_gilist)]
            if user_form_obj.negative_gilist else []),
            *(['-negative_seqidlist',
            'media/' + str(user_form_obj.negative_seqidlist)]
                if user_form_obj.negative_seqidlist else []),
            *(['-taxids', user_form_obj.taxids]
            if user_form_obj.taxids else []),
            *(['-negative_taxids', user_form_obj.negative_taxids]
            if user_form_obj.negative_taxids else []),
            *(['-taxidlist', 'media/' + str(user_form_obj.taxidlist)]
            if user_form_obj.taxidlist else []),
            *(['-negative_taxidlist',
            'media/' + str(user_form_obj.negative_taxidlist)]
                if user_form_obj.negative_taxidlist else []),
            *(['-qcov_hsp_perc', str(user_form_obj.qcov_hsp_perc)]
            if user_form_obj.qcov_hsp_perc else []),
            *(['-max_hsps', str(user_form_obj.max_hsps)]
            if user_form_obj.max_hsps else []),
            *(['-subject_besthit']
            if user_form_obj.subject_besthit else []),
            *(['-parse_deflines']
            if user_form_obj.parse_deflines else []),
            *(['-soft_masking', str(user_form_obj.soft_masking)]
                if user_form_obj.soft_masking else []),
            *(['-lcase_masking']
                if user_form_obj.lcase_masking else []),
            *(['-max_target_seqs', str(user_form_obj.max_target_seqs)]
                if user_form_obj.max_target_seqs else []),
            *(['-max_intron_length', str(user_form_obj.max_intron_length)]
                if user_form_obj.max_intron_length else []),
            *(['-matrix', str(user_form_obj.matrix)]
                if user_form_obj.matrix else []),
        ],
            capture_output=TRUE)

        if running_blastx.stderr:
            if hasattr(database_obj, 'father_database'):
                if not(database_obj.father_database):
                    if not is_multi:
                        # Deleting file if mistakes occured
                        dir_path_input = 'media/blastx_user_inputs/'
                        dir_path_result = 'media/blastx_outputs/'
                        dir_path_params = 'media/blastx_inputs_parameters/'

                        remove_inputs(dir_path_input, user_form_obj.query_file)
                        remove_inputs(dir_path_result,
                            user_form_obj.output_filename)

                        param_file_name = ""
                        if(user_form_obj.gilist):
                            param_file_name = str(user_form_obj.gilist)
                        elif(user_form_obj.seqidlist):
                            param_file_name = str(user_form_obj.seqidlist)
                        elif(user_form_obj.negative_gilist):
                            param_file_name = str(user_form_obj.negative_gilist)
                        elif(user_form_obj.negative_seqidlist):
                            param_file_name = str(user_form_obj.negative_seqidlist)
                        elif(user_form_obj.taxidlist):
                            param_file_name = str(user_form_obj.taxidlist)
                        elif(user_form_obj.negative_taxidlist):
                            param_file_name = str(user_form_obj.negative_taxidlist)

                        if(param_file_name):
                            remove_inputs(dir_path_params, param_file_name)

            # If any errors happend and it has file location,
            # remove the location from it
            running_blastx_error_msg = running_blastx.stderr.decode("utf-8")
            if(re.search('media\/', running_blastx_error_msg)):
                match = re.search(".+?(?=\/)", running_blastx_error_msg)
                part_one = match.group(0)
                match1 = re.search("([^\/]+$)", running_blastx_error_msg)
                part_two = match1.group(0)
                running_blastx_error_msg = part_one + part_two

            return running_blastx_error_msg[:250] + "..."
        else:
            return None

def saveblastx_result(blastx_form_slug):
    # Creating new object or updating it to BlastxResults
    if(BlastxResults.objects.filter(blastx_request=blastx_form_slug).exists()):
        blastx_request = BlastxUserInput.objects.get(
            output_filename=blastx_form_slug)
        BlastxResults.objects.filter(blastx_request=blastx_form_slug) \
            .update(blastx_result='blastx_outputs/' +
                    blastx_request.output_filename)
    else:
        blastx_request = BlastxUserInput.objects.get(
            output_filename=blastx_form_slug)
        new_obj = BlastxResults()
        new_obj.blastx_request = blastx_request
        new_obj.blastx_result = 'blastx_outputs/' + \
            blastx_request.output_filename
        new_obj.save()


def run_tblastx(database_slug, tblastx_form_slug, is_multi):
    # Function to run tblastx
    if(BlastDBData.objects.filter(slug=database_slug).exists()):
        database_obj = BlastDBData.objects.get(slug=database_slug)

        user_form_obj = tBlastxUserInput.objects.get(
            output_filename=tblastx_form_slug)
        
        # Saving database name to find corresponding files
        if(database_obj.user_input):
            database_name = database_obj.user_input.name_of_blast_db

        query_file_dir = 'media/' + str(user_form_obj.query_file)
        database_file_dir = 'media/blast_databases/'
        tblastx_output_dir = 'media/tblastx_outputs/'

        for file_name in os.listdir(tblastx_output_dir):
            if os.path.isfile(os.path.join(tblastx_output_dir, file_name)):
                if re.search("^" + database_name + "\.", file_name):
                    remove_inputs(tblastx_output_dir, database_name)

        running_tblastx = subprocess.run([
            'tblastx',
            '-query', query_file_dir,
            '-db', database_file_dir + database_name,
            '-out', tblastx_output_dir + user_form_obj.output_filename,
            *(['-query_loc', user_form_obj.query_location]
            if user_form_obj.query_location else []),
            *(['-strand', user_form_obj.strand]
            if user_form_obj.strand else []),
            *(['-evalue', str(user_form_obj.evalue)]
            if user_form_obj.evalue else []),
            *(['-word_size', str(user_form_obj.word_size)]
            if user_form_obj.word_size else []),
            *(['-threshold', str(user_form_obj.threshold)]
            if user_form_obj.threshold else []),
            *(['-show_gis']
            if user_form_obj.show_gis else []),
            *(['-line_length', str(user_form_obj.line_length)]
            if user_form_obj.line_length else []),
            *(['-sorthits', user_form_obj.sort_hits]
            if user_form_obj.sort_hits else []),
            *(['-sorthsps', user_form_obj.sort_hsps]
            if user_form_obj.sort_hsps else []),
            *(['-gilist', 'media/' + str(user_form_obj.gilist)]
            if user_form_obj.gilist else []),
            *(['-seqidlist', 'media/' + str(user_form_obj.seqidlist)]
            if user_form_obj.seqidlist else []),
            *(['-negative_gilist', 'media/' + str(user_form_obj.negative_gilist)]
            if user_form_obj.negative_gilist else []),
            *(['-negative_seqidlist',
            'media/' + str(user_form_obj.negative_seqidlist)]
                if user_form_obj.negative_seqidlist else []),
            *(['-taxids', user_form_obj.taxids]
            if user_form_obj.taxids else []),
            *(['-negative_taxids', user_form_obj.negative_taxids]
            if user_form_obj.negative_taxids else []),
            *(['-taxidlist', 'media/' + str(user_form_obj.taxidlist)]
            if user_form_obj.taxidlist else []),
            *(['-negative_taxidlist',
            'media/' + str(user_form_obj.negative_taxidlist)]
                if user_form_obj.negative_taxidlist else []),
            *(['-qcov_hsp_perc', str(user_form_obj.qcov_hsp_perc)]
            if user_form_obj.qcov_hsp_perc else []),
            *(['-max_hsps', str(user_form_obj.max_hsps)]
            if user_form_obj.max_hsps else []),
            *(['-subject_besthit']
            if user_form_obj.subject_besthit else []),
            *(['-parse_deflines']
            if user_form_obj.parse_deflines else []),
            *(['-soft_masking', str(user_form_obj.soft_masking)]
                if user_form_obj.soft_masking else []),
            *(['-lcase_masking']
                if user_form_obj.lcase_masking else []),
            *(['-max_target_seqs', str(user_form_obj.max_target_seqs)]
                if user_form_obj.max_target_seqs else []),
            *(['-matrix', str(user_form_obj.matrix)]
                if user_form_obj.matrix else []),
        ],
            capture_output=TRUE)
        if running_tblastx.stderr:
            if hasattr(database_obj, 'father_database'):
                if not(database_obj.father_database):
                    if not is_multi:
                        # Deleting file if mistakes occured
                        dir_path_input = 'media/tblastx_user_inputs/'
                        dir_path_result = 'media/tblastx_outputs/'
                        dir_path_params = 'media/tblastx_inputs_parameters/'

                        remove_inputs(dir_path_input, user_form_obj.query_file)
                        remove_inputs(dir_path_result, 
                            user_form_obj.output_filename)

                        param_file_name = ""
                        if(user_form_obj.gilist):
                            param_file_name = str(user_form_obj.gilist)
                        elif(user_form_obj.seqidlist):
                            param_file_name = str(user_form_obj.seqidlist)
                        elif(user_form_obj.negative_gilist):
                            param_file_name = str(user_form_obj.negative_gilist)
                        elif(user_form_obj.negative_seqidlist):
                            param_file_name = str(user_form_obj.negative_seqidlist)
                        elif(user_form_obj.taxidlist):
                            param_file_name = str(user_form_obj.taxidlist)
                        elif(user_form_obj.negative_taxidlist):
                            param_file_name = str(user_form_obj.negative_taxidlist)

                        if(param_file_name):
                            remove_inputs(dir_path_params, param_file_name)

            # If any errors happend and it has file location,
            # remove the location from it
            running_tblastx_error_msg = running_tblastx.stderr.decode("utf-8")
            if(re.search('media\/', running_tblastx_error_msg)):
                match = re.search(".+?(?=\/)", running_tblastx_error_msg)
                part_one = match.group(0)
                match1 = re.search("([^\/]+$)", running_tblastx_error_msg)
                part_two = match1.group(0)
                running_tblastx_error_msg = part_one + part_two

            return running_tblastx_error_msg[:250] + "..."
        else:
            return None


def savetblastx_result(tblastx_form_slug):
    # Creating new object or updating it to tBlastxResults
    if(tBlastxResults.objects
    .filter(tblastx_request=tblastx_form_slug).exists()):
        tblastx_request = tBlastxUserInput.objects.get(
            output_filename=tblastx_form_slug)
        tBlastxResults.objects.filter(tblastx_request=tblastx_form_slug) \
            .update(tblastx_result='tblastx_outputs/' +
                    tblastx_request.output_filename)
    else:
        tblastx_request = tBlastxUserInput.objects.get(
            output_filename=tblastx_form_slug)
        new_obj = tBlastxResults()
        new_obj.tblastx_request = tblastx_request
        new_obj.tblastx_result = 'tblastx_outputs/' + \
            tblastx_request.output_filename
        new_obj.save()


def run_tblastn(database_slug, tblastn_form_slug, is_multi):
    # Function for running tblastn using subprocess
    if(BlastDBData.objects.filter(slug=database_slug).exists()):
        database_obj = BlastDBData.objects.get(slug=database_slug)

        user_form_obj = tBlastnUserInput.objects.get(
            output_filename=tblastn_form_slug)
        # Saving database name to find corresponding files
        if(database_obj.user_input):
            database_name = database_obj.user_input.name_of_blast_db

        query_file_dir = 'media/' + str(user_form_obj.query_file)
        database_file_dir = 'media/blast_databases/'
        tblastn_output_dir = 'media/tblastn_outputs/'

        for file_name in os.listdir(tblastn_output_dir):
            if os.path.isfile(os.path.join(tblastn_output_dir, file_name)):
                if re.search("^" + database_name + "\.", file_name):
                    remove_inputs(tblastn_output_dir, database_name)

        running_tblastn = subprocess.run([
            'tblastn',
            '-query', query_file_dir,
            '-db', database_file_dir + database_name,
            '-out', tblastn_output_dir + user_form_obj.output_filename,
            *(['-query_loc', user_form_obj.query_location]
            if user_form_obj.query_location else []),
            *(['-task', user_form_obj.task]
            if user_form_obj.task else []),
            *(['-evalue', str(user_form_obj.evalue)]
            if user_form_obj.evalue else []),
            *(['-word_size', str(user_form_obj.word_size)]
            if user_form_obj.word_size else []),
            *(['-gapopen', str(user_form_obj.gap_open)]
            if user_form_obj.gap_open else []),
            *(['-gapextend', str(user_form_obj.gap_extend)]
            if user_form_obj.gap_extend else []),
            *(['-threshold', str(user_form_obj.threshold)]
            if user_form_obj.threshold else []),
            *(['-show_gis']
            if user_form_obj.show_gis else []),
            *(['-line_length', str(user_form_obj.line_length)]
            if user_form_obj.line_length else []),
            *(['-sorthits', user_form_obj.sort_hits]
            if user_form_obj.sort_hits else []),
            *(['-sorthsps', user_form_obj.sort_hsps]
            if user_form_obj.sort_hsps else []),
            *(['-gilist', 'media/' + str(user_form_obj.gilist)]
            if user_form_obj.gilist else []),
            *(['-seqidlist', 'media/' + str(user_form_obj.seqidlist)]
            if user_form_obj.seqidlist else []),
            *(['-negative_gilist', 'media/' + str(user_form_obj.negative_gilist)]
            if user_form_obj.negative_gilist else []),
            *(['-negative_seqidlist',
            'media/' + str(user_form_obj.negative_seqidlist)]
                if user_form_obj.negative_seqidlist else []),
            *(['-taxids', user_form_obj.taxids]
            if user_form_obj.taxids else []),
            *(['-negative_taxids', user_form_obj.negative_taxids]
            if user_form_obj.negative_taxids else []),
            *(['-taxidlist', 'media/' + str(user_form_obj.taxidlist)]
            if user_form_obj.taxidlist else []),
            *(['-negative_taxidlist',
            'media/' + str(user_form_obj.negative_taxidlist)]
                if user_form_obj.negative_taxidlist else []),
            *(['-qcov_hsp_perc', str(user_form_obj.qcov_hsp_perc)]
            if user_form_obj.qcov_hsp_perc else []),
            *(['-max_hsps', str(user_form_obj.max_hsps)]
            if user_form_obj.max_hsps else []),
            *(['-subject_besthit']
            if user_form_obj.subject_besthit else []),
            *(['-parse_deflines']
            if user_form_obj.parse_deflines else []),
            *(['-soft_masking', str(user_form_obj.soft_masking)]
                if user_form_obj.soft_masking else []),
            *(['-lcase_masking']
                if user_form_obj.lcase_masking else []),
            *(['-max_target_seqs', str(user_form_obj.max_target_seqs)]
                if user_form_obj.max_target_seqs else []),
            *(['-max_intron_length', str(user_form_obj.max_intron_length)]
                if user_form_obj.max_intron_length else []),
        ],
            capture_output=TRUE)

        if running_tblastn.stderr:
            if hasattr(database_obj, 'father_database'):
                if not(database_obj.father_database):
                    if not is_multi:
                        # Deleting file if mistakes occured
                        dir_path_input = 'media/tblastn_user_inputs/'
                        dir_path_result = 'media/tblastn_outputs/'
                        dir_path_params = 'media/tblastn_inputs_parameters/'

                        remove_inputs(dir_path_input, user_form_obj.query_file)
                        remove_inputs(dir_path_result, 
                            user_form_obj.output_filename)

                        param_file_name = ""
                        if(user_form_obj.gilist):
                            param_file_name = str(user_form_obj.gilist)
                        elif(user_form_obj.seqidlist):
                            param_file_name = str(user_form_obj.seqidlist)
                        elif(user_form_obj.negative_gilist):
                            param_file_name = str(user_form_obj.negative_gilist)
                        elif(user_form_obj.negative_seqidlist):
                            param_file_name = str(user_form_obj.negative_seqidlist)
                        elif(user_form_obj.taxidlist):
                            param_file_name = str(user_form_obj.taxidlist)
                        elif(user_form_obj.negative_taxidlist):
                            param_file_name = str(user_form_obj.negative_taxidlist)

                        if(param_file_name):
                            remove_inputs(dir_path_params, param_file_name)

            # If any errors happend and it has file location,
            # remove the location from it
            running_tblastn_error_msg = running_tblastn.stderr.decode("utf-8")
            if(re.search('media\/', running_tblastn_error_msg)):
                match = re.search(".+?(?=\/)", running_tblastn_error_msg)
                part_one = match.group(0)
                match1 = re.search("([^\/]+$)", running_tblastn_error_msg)
                part_two = match1.group(0)
                running_tblastn_error_msg = part_one + part_two

            return running_tblastn_error_msg[:250] + "..."
        else:
            return None


def savetblastn_result(tblastn_form_slug):
    # Creating new object or updating it to tBlastnResults
    if(tBlastnResults.objects
    .filter(tblastn_request=tblastn_form_slug).exists()):
        tblastn_request = tBlastnUserInput.objects.get(
            output_filename=tblastn_form_slug)
        tBlastnResults.objects.filter(tblastn_request=tblastn_form_slug) \
            .update(tblastn_result='tblastn_outputs/' +
                    tblastn_request.output_filename)
    else:
        tblastn_request = tBlastnUserInput.objects.get(
            output_filename=tblastn_form_slug)
        new_obj = tBlastnResults()
        new_obj.tblastn_request = tblastn_request
        new_obj.tblastn_result = 'tblastn_outputs/' + \
            tblastn_request.output_filename
        new_obj.save()


def all_alignment_update(alignment, updated_db):
    # Finding the father aligment and creating child user input 
    if(BlastpUserInput.objects
        .filter(output_filename=alignment.output_filename).exists()):
        # Creating BlastpUserInput
        obj = BlastpUserInput.objects \
            .get(output_filename=alignment.output_filename)
        if(obj):
            obj.database = updated_db
            obj.batch_align = None
            obj.created = timezone.now()
            obj.save()
            return obj

    elif(BlastnUserInput.objects
            .filter(output_filename=alignment.output_filename).exists()):
        # Creating BlastnUserInput
        obj = BlastnUserInput.objects \
            .get(output_filename=alignment.output_filename)
        if(obj):
            obj.database = updated_db
            obj.batch_align = None
            obj.created = timezone.now()
            obj.save()
            return obj
        
    elif(BlastxUserInput.objects
            .filter(output_filename=alignment.output_filename).exists()):
        # Creating BlastxUserInput
        obj = BlastxUserInput.objects \
            .get(output_filename=alignment.output_filename)
        if(obj):
            obj.database = updated_db
            obj.batch_align = None
            obj.created = timezone.now()
            obj.save()
            return obj
        
    elif(tBlastnUserInput.objects
            .filter(output_filename=alignment.output_filename).exists()):
        # Creating tBlastnUserInput
        obj = tBlastnUserInput.objects \
            .get(output_filename=alignment.output_filename)
        if(obj):
            obj.database = updated_db
            obj.batch_align = None
            obj.created = timezone.now()
            obj.save()
            return obj
        
    elif(tBlastxUserInput.objects 
            .filter(output_filename=alignment.output_filename).exists()):
        # Creating tBlastxUserInput
        obj = tBlastxUserInput.objects \
            .get(output_filename=alignment.output_filename)
        if(obj):
            obj.database = updated_db
            obj.batch_align = None
            obj.created = timezone.now()
            obj.save()
            return obj
    else:
        return None

def generate_unique_filename(filename, db_user_input):
    # Generate random identificator
    random_2 = string.ascii_letters.lower() + string.digits
    random.seed = (os.urandom(1024))
    random_id = "".join(random.choice(random_2) for i in range(2))
    name = F'{filename}-{random_id}'

    # Creating DB name
    if(db_user_input.objects.filter(output_filename=name).exists()):
        generate_unique_filename(filename, db_user_input)
    else:
        return name

def remove_blastn_alignment(obj_name):
    remove_alignment_files(
        BlastnUserInput, 
        'media/blastn_user_inputs/', 
        'media/blastn_inputs_parameters/', 
        'media/blastn_outputs/', 
        obj_name
    )
  

def remove_blastp_alignment(obj_name):
    remove_alignment_files(
        BlastpUserInput,
        'media/blastp_user_inputs/',
        'media/blastp_inputs_parameters/',
        'media/blastp_outputs/',
        obj_name
    )


def remove_blastx_alignment(obj_name):
    remove_alignment_files(
        BlastxUserInput,
        'media/blastx_user_inputs/',
        'media/blastx_inputs_parameters/',
        'media/blastx_outputs/',
        obj_name
    )


def remove_tblastx_alignment(obj_name):
    remove_alignment_files(
        tBlastxUserInput,
        'media/tblastx_user_inputs/',
        'media/tblastx_inputs_parameters/',
        'media/tblastx_outputs/',
        obj_name
    )


def remove_tblastn_alignment(obj_name):
    remove_alignment_files(
        tBlastnUserInput,
        'media/tblastn_user_inputs/',
        'media/tblastn_inputs_parameters/',
        'media/tblastn_outputs/',
        obj_name
    )

def remove_alignment_files(model_class, user_input_path, input_param_path, 
    output_path, obj_name):
    obj = model_class.objects.filter(output_filename=obj_name).first()
    if obj:
        # Removing files
        if obj.output_filename:
            remove_inputs(output_path, obj.output_filename)
        if obj.query_file:
            remove_inputs(user_input_path, obj.query_file)
        if obj.gilist:
            remove_inputs(input_param_path, obj.gilist)
        elif obj.seqidlist:
            remove_inputs(input_param_path, obj.seqidlist)
        elif obj.negative_gilist:
            remove_inputs(input_param_path, obj.negative_gilist)
        elif obj.negative_seqidlist:
            remove_inputs(input_param_path, obj.negative_seqidlist)
        elif obj.taxidlist:
            remove_inputs(input_param_path, obj.taxidlist)
        elif obj.negative_taxidlist:
            remove_inputs(input_param_path, obj.negative_taxidlist)
        # Removing actual object
        obj.delete()

    logger.info(
        f"Removing alignments results, their objects and input files."
    )
