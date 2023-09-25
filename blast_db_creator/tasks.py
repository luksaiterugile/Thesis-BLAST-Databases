from celery import shared_task, chain
from django_celery_results.models import TaskResult

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
from django.http import Http404
from django.contrib import messages
from zipfile import ZipFile
from django.http import JsonResponse

from .utils import *

import subprocess
import os
import re
import string
import random
import json
import logging
from django.utils import timezone

from celery.utils.log import get_task_logger

logger = get_task_logger("blast_db_creator")


@shared_task(bind=True, name="Creating a BLAST database")
def createdb_task(self, name, user_id):
    # Step 1: Creating BLAST database
    error_blast = createdb(name, False)
    if error_blast:
        # If there were errors, raise Exception
        user_input_obj = UserInput.objects.get(
            name_of_blast_db=name)
        user_input_obj.delete()
        logger.warning(
            f"Could not create BLAST database: \"{name}\". "
            f"Error from \"makeblastdb\" program: {error_blast} ")
        raise Exception(str(error_blast))
    
    # Step 2: Saving BLAST database to model
    saveblastdb_data(name)

    logger.info(f"BLAST database: \"{name}\" was created successfully.")

    # Task completed successfully
    return {'state': 'SUCCESS', 'task_id': self.request.id}


@shared_task(bind=True, name="Running BLASTn program")
def blastn_task(self, slug, name, is_multi, user_id):
    # Step 1: Running BLASTn program for one BLAST DB
    error_blastn = run_blastn(slug, name, is_multi)

    if error_blastn:
        created_obj = BlastnUserInput.objects \
            .get(output_filename=name)
        created_obj.delete()
        logger.warning(
            f"Could not search for similar sequences using \"blastn\" program."
            f"Errors received: {error_blastn}."
        )
        raise Exception(str(error_blastn))

    # Step 2: Saving BLASTn result to model
    saveblastn_result(name)

    logger.info(
        f"Search for similar sequences using \"blastn\" program finished "
        f"succesfully. ")

    # Task completed succesfully
    return {'state': 'SUCCESS', 'task_id': self.request.id}
    

@shared_task(bind=True, name="Running BLASTn program for alignments update")
def blastn_update_task(self, slug, name, is_multi, user_id):
    # Step 1: Running BLASTn program for alignments update
    error_blastn = run_blastn(slug, name, is_multi)

    if error_blastn:
        created_obj = BlastnUserInput.objects \
            .get(output_filename=name)
        created_obj.delete()
        logger.warning(
            f"Could not update alignments results using \"blastn\" program."
            f"Errors received: {error_blastn}."
        )
        raise Exception(str(error_blastn))

    # Step 2: Saving BLASTn result to model
    saveblastn_result(name)

    logger.info(
        f"Succesfully updated alignments results using \"blastn\" program."
    )

    # Task completed succesfully
    return {'state': 'SUCCESS', 'task_id': self.request.id}


@shared_task(bind=True, name="Running BLASTp program")
def blastp_task(self, slug, name, is_multi, user_id):
    # Step 1: Running BLASTp program for one BLAST DB
    error_blastp = run_blastp(slug, name, is_multi)

    if error_blastp:
        created_obj = BlastpUserInput.objects \
            .get(output_filename=name)
        created_obj.delete()
        logger.warning(
            f"Could not search for similar sequences using \"blastp\" program."
            f"Errors received: {error_blastp}."
        )
        raise Exception(str(error_blastp))

    # Step 2: Saving BLASTp result to model
    saveblastp_result(name)

    logger.info(
        f"Search for similar sequences using \"blastp\" program finished "
        f"succesfully. ")

    # Task completed succesfully
    return {'state': 'SUCCESS', 'task_id': self.request.id}

@shared_task(bind=True, name="Running BLASTp program for alignments update")
def blastp_update_task(self, slug, name, is_multi, user_id):
    # Step 1: Running BLASTp program for alignments update
    error_blastp = run_blastp(slug, name, is_multi)

    if error_blastp:
        created_obj = BlastpUserInput.objects \
            .get(output_filename=name)
        created_obj.delete()
        logger.warning(
            f"Could not update alignments results using \"blastp\" program."
            f"Errors received: {error_blastn}."
        )
        raise Exception(str(error_blastp))

    # Step 2: Saving BLASTp result to model
    saveblastp_result(name)

    logger.info(
        f"Succesfully updated alignments results using \"blastp\" program."
    )

    # Task completed succesfully
    return {'state': 'SUCCESS', 'task_id': self.request.id}


@shared_task(bind=True, name="Running BLASTx program")
def blastx_task(self, slug, name, is_multi, user_id):
    # Step 1: Running BLASTx program for one BLAST DB
    error_blastx = run_blastx(slug, name, is_multi)

    if error_blastx:
        created_obj = BlastxUserInput.objects \
            .get(output_filename=name)
        created_obj.delete()
        logger.warning(
            f"Could not search for similar sequences using \"blastx\" program."
            f"Errors received: {error_blastx}."
        )
        raise Exception(str(error_blastx))

    # Step 2: Saving BLASTx result to model
    saveblastx_result(name)

    logger.info(
        f"Search for similar sequences using \"blastx\" program finished "
        f"succesfully. ")

    # Task completed succesfully
    return {'state': 'SUCCESS', 'task_id': self.request.id}


@shared_task(bind=True, name="Running BLASTx program for alignments update")
def blastx_update_task(self, slug, name, is_multi, user_id):
    # Step 1: Running BLASTx program for alignments update
    error_blastx = run_blastx(slug, name, is_multi)

    if error_blastx:
        created_obj = BlastxUserInput.objects \
            .get(output_filename=name)
        created_obj.delete()
        logger.warning(
            f"Could not update alignments results using \"blastx\" program."
            f"Errors received: {error_blastn}."
        )
        raise Exception(str(error_blastx))

    # Step 2: Saving BLASTx result to model
    saveblastx_result(name)
    logger.info(
        f"Succesfully updated alignments results using \"blastx\" program."
    )

    # Task completed succesfully
    return {'state': 'SUCCESS', 'task_id': self.request.id}


@shared_task(bind=True, name="Running tBLASTx program")
def tblastx_task(self, slug, name, is_multi, user_id):
    # Step 1: Running tBLASTx program for one BLAST DB
    error_tblastx = run_tblastx(slug, name, is_multi)

    if error_tblastx:
        created_obj = tBlastxUserInput.objects \
            .get(output_filename=name)
        created_obj.delete()
        logger.warning(
            f"Could not search for similar sequences using \"tblastx\" program."
            f"Errors received: {error_tblastx}."
        )
        raise Exception(str(error_tblastx))

    # Step 2: Saving tBLASTx result to model
    savetblastx_result(name)

    logger.info(
        f"Search for similar sequences using \"tblastx\" program finished "
        f"succesfully. ")

    # Task completed succesfully
    return {'state': 'SUCCESS', 'task_id': self.request.id}


@shared_task(bind=True, name="Running tBLASTx program for alignments update")
def tblastx_update_task(self, slug, name, is_multi, user_id):
    # Step 1: Running tBLASTx program for one BLAST DB
    error_tblastx = run_tblastx(slug, name, is_multi)

    if error_tblastx:
        created_obj = tBlastxUserInput.objects \
            .get(output_filename=name)
        created_obj.delete()
        logger.warning(
            f"Could not update alignment results using \"tblastx\" program."
            f"Errors received: {error_blastn}."
        )
        raise Exception(str(error_tblastx))

    # Step 2: Saving tBLASTx result to model
    savetblastx_result(name)
    logger.info(
        f"Succesfully updated alignments results using \"tblastx\" program."
    )

    # Task completed succesfully
    return {'state': 'SUCCESS', 'task_id': self.request.id}


@shared_task(bind=True, name="Running tBLASTn program")
def tblastn_task(self, slug, name, is_multi, user_id):
    # Step 1: Running tBLASTn program for one BLAST DB
    error_tblastn = run_tblastn(slug, name, False)

    if error_tblastn:
        created_obj = tBlastnUserInput.objects \
            .get(output_filename=name)
        created_obj.delete()
        logger.warning(
            f"Could not search for similar sequences using \"tblastn\" program."
            f"Errors received: {error_tblastn}."
        )
        raise Exception(str(error_tblastn))

    # Step 2: Saving tBLASTn result to model
    savetblastn_result(name)

    logger.info(
        f"Search for similar sequences using \"tblastn\" program finished "
        f"succesfully. ")

    # Task completed succesfully
    return {'state': 'SUCCESS', 'task_id': self.request.id}


@shared_task(bind=True, name="Running tBLASTn program for alignments update")
def tblastn_update_task(self, slug, name, is_multi, user_id):
    # Step 1: Running tBLASTn program for one BLAST DB
    error_tblastn = run_tblastn(slug, name, False)

    if error_tblastn:
        created_obj = tBlastnUserInput.objects \
            .get(output_filename=name)
        created_obj.delete()
        logger.warning(
            f"Could not update alignment results using \"tblastn\" program."
            f"Errors received: {error_blastn}."
        )
        raise Exception(str(error_tblastn))

    # Step 2: Saving tBLASTn result to model
    savetblastn_result(name)
    logger.info(
        f"Succesfully updated alignments results using \"tblastn\" program."
    )

    # Task completed succesfully
    return {'state': 'SUCCESS', 'task_id': self.request.id}


@shared_task(bind=True, name="Updating BLAST database")
def createdb_update_task(self, name, father_db, user_id):
    # Step 1: Creating BLAST database
    error_blast = createdb(name, True)
    if error_blast:
        # If there were errors, raise Exception
        user_input_obj = UserInput.objects.get(
            name_of_blast_db=name)
        # Remove input file
        remove_inputs('media/blast_db_updates/', str(user_input_obj.input_file))
        user_input_obj.delete()
        logger.warning(
            f"Could not update BLAST database: \"{father_db}\". "
            f"Error from \"makeblastdb\" program: {error_blast} ")
        raise Exception(str(error_blast))
    
    # Step 2: Saving BLAST database to model
    saveblastdb_data(name)
    logger.info(f"BLAST database: \"{name}\" was created successfully.")

    # Step 3: Update BlastDBData and UpdateBlastDB objects
    updated_db = BlastDBData.objects.filter(slug=name).first()
    if updated_db:
        if UpdateBlastDB.objects.filter(user_input=name).exists():
            current_update = UpdateBlastDB.objects \
                .filter(user_input=name).first()
            if current_update:
                # Insert foreign key to BlastDBData
                UpdateBlastDB.objects.filter(user_input=name).update(
                    database=updated_db,
                )

        father_db_obj = BlastDBData.objects.filter(slug=father_db).first()
        if(father_db_obj):
            # Insert father_db name to BlastDBData object
            BlastDBData.objects.filter(slug=name).update(
                father_database=father_db_obj
            )
        logger.info(
            f"BLAST database: \"{name}\" information was saved "
            f"successfully.")
    else:
        logger.warning(
            f"Information for BLAST database: \"{name}\". "
            f"Could not be saved. ")
        raise Exception("Could not update the BLAST database. \
            Please try again")
        
    # Task completed successfully
    return {'state': 'SUCCESS', 'task_id': self.request.id}


@shared_task(bind=True, name="Updating BLASTp alignments")
def update_blastp_alignments(self, alignments, name, user_id):
    blastp_errors_alignments = {}

    # Retrieve updated BLAST DB
    updated_db = BlastDBData.objects.filter(slug=name).first()

    if updated_db:
        for alignment in alignments:
            alignment_obj = BlastpUserInput.objects \
                .filter(output_filename=alignment).first()

            if alignment_obj:
                try:
                    update_align = all_alignment_update(
                        alignment_obj, updated_db)
                    if update_align:
                        # Running BLASTp program
                        error_blastp = run_blastp(
                            updated_db.slug, 
                            update_align.output_filename, 
                            True)
                        
                        if error_blastp:
                            created_obj = BlastpUserInput.objects \
                                .filter(output_filename=
                                    update_align.output_filename)
                            created_obj.delete()
                            blastp_errors_alignments[
                                update_align.output_filename
                                ]= str(error_blastp)[:250]
                            continue
                        else:
                            saveblastp_result(update_align.output_filename)
                    else:
                        # If alignment not found, was not created
                        continue
                except: 
                    continue
                else:
                    continue
            else:
                continue

        if(len(blastp_errors_alignments) == len(alignments)):
            logger.warning(
                f"Could not update alignments results using \"blastp\" program."
                f" One of the errors received: "
                f"{next(iter(blastp_errors_alignments.values()))}."
            )
            raise Exception(blastp_errors_alignments)
    else:
        logger.warning(
            f"Could not update BLAST database: \"{name}\". ")
        raise Exception("Could not update the BLAST database. \
            Please try again")

    if(blastp_errors_alignments):
        # Task completed partly successfully
        logger.info(
            f"Update of alignments results using \"blastp\" program was "
            f"partly successful."
        )
        return {'state': 'SUCCESS', 
                'task_id': self.request.id, 
                'info': blastp_errors_alignments}
    else:
        # Task completed successfully
        logger.info(
            f"Succesfully updated alignments results using \"blastp\" program."
        )
        return {'state': 'SUCCESS', 'task_id': self.request.id}

@shared_task(bind=True, name="Updating BLASTx alignments")
def update_blastx_alignments(self, alignments, name, user_id):
    blastx_errors_alignments = {}

    # Retrieve updated BLAST DB
    updated_db = BlastDBData.objects.filter(slug=name).first()

    if updated_db:
        for alignment in alignments:
            # Retrieve father alignment user input
            alignment_obj = BlastxUserInput.objects \
                .filter(output_filename=alignment).first()

            if alignment_obj:
                try:
                    update_align = all_alignment_update(
                        alignment_obj, updated_db)
                    if update_align:
                        # Running BLASTx program
                        error_blastx = run_blastx(
                            updated_db.slug, 
                            update_align.output_filename, 
                            True)
                        
                        if error_blastx:
                            created_obj = BlastxUserInput.objects \
                                .filter(output_filename=
                                    update_align.output_filename)
                            created_obj.delete()
                            blastx_errors_alignments[
                                update_align.output_filename
                                ]= str(error_blastx)[:250]
                            continue
                        else:
                            saveblastx_result(update_align.output_filename)
                    else:
                        # If alignment not found, was not created
                        continue
                except: 
                    continue
                else:
                    continue
            else:
                continue

        if(len(blastx_errors_alignments) == len(alignments)):
            logger.warning(
                f"Could not update alignments results using \"blastx\" program."
                f" One of the errors received: "
                f"{next(iter(blastx_errors_alignments.values()))}."
            )
            raise Exception(blastx_errors_alignments)
    else:
        logger.warning(
            f"Could not update BLAST database: \"{name}\". ")
        raise Exception("Could not update the BLAST database. \
            Please try again")

    if(blastx_errors_alignments):
        # Task completed partly successfully
        logger.info(
            f"Update of alignments results using \"blastx\" program was "
            f"partly successful."
        )
        return {'state': 'SUCCESS', 
                'task_id': self.request.id, 
                'info': blastx_errors_alignments}
    else:
        # Task completed successfully
        logger.info(
            f"Succesfully updated alignments results using \"blastx\" program."
        )
        return {'state': 'SUCCESS', 'task_id': self.request.id}

@shared_task(bind=True, name="Updating tBLASTx alignments")
def update_tblastx_alignments(self, alignments, name, user_id):
    tblastx_errors_alignments = {}

    # Retrieve updated BLAST DB
    updated_db = BlastDBData.objects.filter(slug=name).first()

    if updated_db:
        for alignment in alignments:
            alignment_obj = tBlastxUserInput.objects \
                .filter(output_filename=alignment).first()

            if alignment_obj:
                try:
                    update_align = all_alignment_update(
                        alignment_obj, updated_db)
                    if update_align:
                        # Running tBLASTx program
                        error_tblastx = run_tblastx(
                            updated_db.slug, 
                            update_align.output_filename, 
                            True)
                        
                        if error_tblastx:
                            created_obj = tBlastxUserInput.objects \
                                .filter(output_filename=
                                    update_align.output_filename)
                            created_obj.delete()
                            tblastx_errors_alignments[
                                update_align.output_filename
                                ]= str(error_tblastx)[:250]
                            continue
                        else:
                            savetblastx_result(update_align.output_filename)
                    else:
                        # If alignment not found, was not created
                        continue
                except: 
                    continue
                else:
                    continue
            else:
                continue

        if(len(tblastx_errors_alignments) == len(alignments)):
            logger.warning(
                f"Could not update alignments "
                f"results using \"tblastx\" program."
                f" One of the errors received: "
                f"{next(iter(tblastx_errors_alignments.values()))}."
            )
            raise Exception(tblastx_errors_alignments)
    else:
        logger.warning(
            f"Could not update BLAST database: \"{name}\". ")
        raise Exception("Could not update the BLAST database. \
            Please try again")

    if(tblastx_errors_alignments):
        # Task completed partly successfully
        logger.info(
            f"Update of alignments results using \"tblastx\" program was "
            f"partly successful."
        )
        return {'state': 'SUCCESS', 
                'task_id': self.request.id, 
                'info': tblastx_errors_alignments}
    else:
        logger.info(
            f"Succesfully updated alignments results using \"tblastx\" program."
        )
        # Task completed successfully
        return {'state': 'SUCCESS', 'task_id': self.request.id}


@shared_task(bind=True, name="Updating tBLASTn alignments")
def update_tblastn_alignments(self, alignments, name, user_id):
    tblastn_errors_alignments = {}

    # Retrieve updated BLAST DB
    updated_db = BlastDBData.objects.filter(slug=name).first()

    if updated_db:
        for alignment in alignments:
            alignment_obj = tBlastnUserInput.objects \
                .filter(output_filename=alignment).first()

            if alignment_obj:
                try:
                    update_align = all_alignment_update(
                        alignment_obj, updated_db)
                    if update_align:
                        # Running tBLASTn program
                        error_tblastn = run_tblastn(
                            updated_db.slug, 
                            update_align.output_filename, 
                            True)
                        
                        if error_tblastn:
                            created_obj = tBlastnUserInput.objects \
                                .filter(output_filename=
                                    update_align.output_filename)
                            created_obj.delete()
                            tblastn_errors_alignments[
                                update_align.output_filename
                                ]= str(error_tblastn)[:250]
                            continue
                        else:
                            savetblastn_result(update_align.output_filename)
                    else:
                        # If alignment not found, was not created
                        continue
                except: 
                    continue
                else:
                    continue
            else:
                continue

        if(len(tblastn_errors_alignments) == len(alignments)):
            logger.warning(
                f"Could not update alignments results "
                f"using \"tblastn\" program."
                f" One of the errors received: "
                f"{next(iter(tblastn_errors_alignments.values()))}."
            )
            raise Exception(tblastn_errors_alignments)
    else:
        logger.warning(
            f"Could not update BLAST database: \"{name}\". ")
        raise Exception("Could not update the BLAST database. \
            Please try again")

    if(tblastn_errors_alignments):
        # Task completed partly successfully
        logger.info(
            f"Update of alignments results using \"tblastn\" program was "
            f"partly successful."
        )
        return {'state': 'SUCCESS', 
                'task_id': self.request.id, 
                'info': tblastn_errors_alignments}
    else:
        # Task completed successfully
        logger.info(
            f"Succesfully updated alignments results using \"tblastn\" program."
        )
        return {'state': 'SUCCESS', 'task_id': self.request.id}

@shared_task(bind=True, name="Updating BLASTn alignments")
def update_blastn_alignments(self, alignments, name, user_id):
    blastn_errors_alignments = {}

    # Retrieve updated BLAST DB
    updated_db = BlastDBData.objects.filter(slug=name).first()

    if updated_db:
        for alignment in alignments:
            alignment_obj = BlastnUserInput.objects \
                .filter(output_filename=alignment).first()

            if alignment_obj:
                try:
                    update_align = all_alignment_update(
                        alignment_obj, updated_db)
                    if update_align:
                        # Running BLASTn program
                        error_blastn = run_blastn(
                            updated_db.slug, 
                            update_align.output_filename, 
                            True)
                        
                        if error_blastn:
                            created_obj = BlastnUserInput.objects \
                                .filter(output_filename=
                                    update_align.output_filename)
                            created_obj.delete()
                            blastn_errors_alignments[
                                update_align.output_filename
                                ]= str(error_blastn)[:250]
                            continue
                        else:
                            saveblastn_result(update_align.output_filename)
                    else:
                        # If alignment not found, was not created
                        continue
                except: 
                    continue
                else:
                    continue
            else:
                continue

        if(len(blastn_errors_alignments) == len(alignments)):
            logger.warning(
                f"Could not update alignments results using \"blastn\" program."
                f" One of the errors received: "
                f"{next(iter(blastn_errors_alignments.values()))}."
            )
            raise Exception(blastn_errors_alignments)
    else:
        logger.warning(
            f"Could not update BLAST database: \"{name}\". ")
        raise Exception("Could not update the BLAST database. \
            Please try again")

    if(blastn_errors_alignments):
        # Task completed partly successfully
        logger.info(
            f"Update of alignments results using \"blastn\" program was "
            f"partly successful."
        )
        return {'state': 'SUCCESS', 
                'task_id': self.request.id, 
                'info': blastn_errors_alignments}
    else:
        # Task completed successfully
        logger.info(
            f"Succesfully updated alignments results using \"blastn\" program."
        )
        return {'state': 'SUCCESS', 'task_id': self.request.id}


@shared_task(bind=True, name="Generating batch BLASTn alignments")
def batch_blastn_alignments(self, align_filenames, batch_id, user_id):
    errors = {}

    for filename in align_filenames:
        try: 
            created_obj = BlastnUserInput.objects \
                .filter(output_filename=filename).first()
            
            if not created_obj:
                continue
            else:
                # Run BLASTn program
                error_blastn = run_blastn(created_obj.database.slug, 
                    created_obj.output_filename, True)

                if error_blastn:
                    errors[filename] = str(error_blastn)[:250]
                    if(created_obj.output_filename):
                        remove_inputs('media/blastn_outputs/',
                            str(created_obj.output_filename))
                    continue
                else:
                    saveblastn_result(created_obj.output_filename)

        except Exception as exc:
            continue
        else:
            continue    
    
    if(len(errors) == len(align_filenames)):
        # Remove input files and objects
        for filename in align_filenames:
            created_obj = BlastnUserInput.objects \
                .filter(output_filename=filename).first()
            remove_blastn_alignment(str(created_obj.output_filename))
            created_obj.delete()

        logger.warning(
            f"Could not generate batch alignments for many BLAST databases"
            f"using \"blastn\" program."
            f"One of the errors received: "
            f"{next(iter(errors.values()))}"
        )
        raise Exception(errors)

    if errors:
        # Task completed partly succesfully
        logger.info(
            f"Batch alignment generation for many BLAST databases using "
            f"\"blastn\" program was partly successful."
        )
        return {'state': 'SUCCESS', 'task_id': self.request.id, 'info': errors}
    else:
        # Task completed successfully
        logger.info(
            f"Batch alignment generation for many BLAST databases using "
            f"\"blastn\" program was successful."
        )
        return {'state': 'SUCCESS', 'task_id': self.request.id}


@shared_task(bind=True, name="Generating batch BLASTx alignments")
def batch_blastx_alignments(self, align_filenames, batch_id, user_id):
    errors = {}
    
    for filename in align_filenames:
        try: 
            created_obj = BlastxUserInput.objects \
                .filter(output_filename=filename).first()
            
            if not created_obj:
                continue
            else:
                # Run BLASTx program
                error_blastx = run_blastx(created_obj.database.slug, 
                    created_obj.output_filename, True)

                if error_blastx:
                    errors[filename] = str(error_blastx)[:250]
                    if(created_obj.output_filename):
                        remove_inputs('media/blastx_outputs/',
                            str(created_obj.output_filename))
                    continue
                else:
                    saveblastx_result(created_obj.output_filename)

        except Exception as exc:
            continue
        else:
            continue
            
    if(len(errors) == len(align_filenames)):
        # Remove input files and objects
        for filename in align_filenames:
            created_obj = BlastxUserInput.objects \
                .filter(output_filename=filename).first()
            remove_blastx_alignment(str(created_obj.output_filename))
            created_obj.delete()

        logger.warning(
            f"Could not generate batch alignments for many BLAST databases"
            f"using \"blastx\" program."
            f"One of the errors received: "
            f"{next(iter(errors.values()))}"
        )
        raise Exception(errors)

    if errors:
        # Task completed partly succesfully
        logger.info(
            f"Batch alignment generation for many BLAST databases using "
            f"\"blastx\" program was partly successful."
        )
        return {'state': 'SUCCESS', 'task_id': self.request.id, 'info': errors}
    else:
        # Task completed successfully
        logger.info(
            f"Batch alignment generation for many BLAST databases using "
            f"\"blastx\" program was successful."
        )
        return {'state': 'SUCCESS', 'task_id': self.request.id}


@shared_task(bind=True, name="Generating batch BLASTp alignments")
def batch_blastp_alignments(self, align_filenames, batch_id, user_id):
    errors = {}
    for filename in align_filenames:
        try: 
            created_obj = BlastpUserInput.objects \
                .filter(output_filename=filename).first()
            
            if not created_obj:
                continue
            else:
                # Run BLASTp program
                error_blastp = run_blastp(created_obj.database.slug, 
                    created_obj.output_filename, True)

                if error_blastp:
                    errors[filename] = str(error_blastp)[:250]
                    if(created_obj.output_filename):
                        remove_inputs('media/blastp_outputs/',
                            str(created_obj.output_filename))
                    continue
                else:
                    saveblastp_result(created_obj.output_filename)

        except Exception as exc:
            continue
        else:
            continue
            
    if(len(errors) == len(align_filenames)):
        # Remove input files and objects
        for filename in align_filenames:
            created_obj = BlastpUserInput.objects \
                .filter(output_filename=filename).first()
            remove_blastp_alignment(str(created_obj.output_filename))
            created_obj.delete()

        logger.warning(
            f"Could not generate batch alignments for many BLAST databases"
            f"using \"blastp\" program."
            f"One of the errors received: "
            f"{next(iter(errors.values()))}"
        )
        raise Exception(errors)

    if errors:
        # Task completed partly succesfully
        logger.info(
            f"Batch alignment generation for many BLAST databases using "
            f"\"blastp\" program was partly successful."
        )
        return {'state': 'SUCCESS', 'task_id': self.request.id, 'info': errors}
    else:
        # Task completed successfully
        logger.info(
            f"Batch alignment generation for many BLAST databases using "
            f"\"blastp\" program was successful."
        )
        return {'state': 'SUCCESS', 'task_id': self.request.id}

@shared_task(bind=True, name="Generating batch tBLASTn alignments")
def batch_tblastn_alignments(self, align_filenames, batch_id, user_id):
    errors = {}
    
    for filename in align_filenames:
        try: 
            created_obj = tBlastnUserInput.objects \
                .filter(output_filename=filename).first()
            
            if not created_obj:
                continue
            else:
                # Run tBLASTn program
                error_tblastn = run_tblastn(created_obj.database.slug, 
                    created_obj.output_filename, True)

                if error_tblastn:
                    errors[filename] = str(error_tblastn)[:250]
                    if(created_obj.output_filename):
                        remove_inputs('media/tblastn_outputs/',
                            str(created_obj.output_filename))
                    continue
                else:
                    savetblastn_result(created_obj.output_filename)

        except Exception as exc:
            continue
        else:
            continue
            
    if(len(errors) == len(align_filenames)):
        # Remove input files and objects
        for filename in align_filenames:
            created_obj = tBlastnUserInput.objects \
                .filter(output_filename=filename).first()
            remove_tblastn_alignment(str(created_obj.output_filename))
            created_obj.delete()

        logger.warning(
            f"Could not generate batch alignments for many BLAST databases"
            f"using \"tblastn\" program."
            f"One of the errors received: "
            f"{next(iter(errors.values()))}"
        )
        raise Exception(errors)

    if errors:
        # Task completed partly succesfully
        logger.info(
            f"Batch alignment generation for many BLAST databases using "
            f"\"tblastn\" program was partly successful."
        )
        return {'state': 'SUCCESS', 'task_id': self.request.id, 'info': errors}
    else:
        # Task completed successfully
        logger.info(
            f"Batch alignment generation for many BLAST databases using "
            f"\"tblastn\" program was successful."
        )
        return {'state': 'SUCCESS', 'task_id': self.request.id}

@shared_task(bind=True, name="Generating batch tBLASTx alignments")
def batch_tblastx_alignments(self, align_filenames, batch_id, user_id):
    errors = {}
    
    for filename in align_filenames:
        try: 
            created_obj = tBlastxUserInput.objects \
                .filter(output_filename=filename).first()
            
            if not created_obj:
                continue
            else:
                # Run tBLASTx program
                error_tblastx = run_tblastx(created_obj.database.slug, 
                    created_obj.output_filename, True)

                if error_tblastx:
                    errors[filename] = str(error_tblastx)[:250]
                    if(created_obj.output_filename):
                        remove_inputs('media/tblastx_outputs/',
                            str(created_obj.output_filename))
                    continue
                else:
                    savetblastx_result(created_obj.output_filename)

        except Exception as exc:
            continue
        else:
            continue
            
    if(len(errors) == len(align_filenames)):
        # Remove input files and objects
        for filename in align_filenames:
            created_obj = tBlastxUserInput.objects \
                .filter(output_filename=filename).first()
            remove_tblastx_alignment(str(created_obj.output_filename))
            created_obj.delete()

        logger.warning(
            f"Could not generate batch alignments for many BLAST databases"
            f"using \"tblastx\" program."
            f"One of the errors received: "
            f"{next(iter(errors.values()))}"
        )
        raise Exception(errors)

    if errors:
        # Task completed partly succesfully
        logger.info(
            f"Batch alignment generation for many BLAST databases using "
            f"\"tblastx\" program was partly successful."
        )
        return {'state': 'SUCCESS', 'task_id': self.request.id, 'info': errors}
    else:
        # Task completed successfully
        logger.info(
            f"Batch alignment generation for many BLAST databases using "
            f"\"tblastx\" program was successful."
        )
        return {'state': 'SUCCESS', 'task_id': self.request.id}