from logging import PlaceHolder
from logging.handlers import SMTPHandler
from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import pre_save, post_save
from django.core.validators import FileExtensionValidator
from django.utils.text import slugify
from django.utils import timezone
from django.core.validators import MaxValueValidator, MinValueValidator
from django.core.validators import validate_comma_separated_integer_list
import os
import random
import re
from django import forms
import string
from django_celery_results.models import TaskResult


class UserInput(models.Model):
    # Creating 2D vectors for choice fields
    DB_types = (
        ("nucl", "Nucleotide"),
        ("prot", "Protein"),
    )

    file_types = (
        ("fasta", "Fasta"),
    )

    version = (
        ("4", "4"),
        ("5", "5"),
    )

    public_private = (
        ("public", "Public"),
        ("private", "Private"),
    )

    public_or_private = models.CharField(max_length=12, choices=public_private,
                                         default="public")

    user = models.ForeignKey(User, on_delete=models.CASCADE, blank=True,
                             null=True)
    

    # Required arguments:
    input_file = models.FileField(upload_to='users_inputs/', validators=[
        FileExtensionValidator(allowed_extensions=['fasta'])])
    database_type = models.CharField(
        max_length=12, choices=DB_types, default="nucl")

    # Optional/default arguments:
    input_type = models.CharField(
        max_length=12, choices=file_types, default="fasta")

    name_of_blast_db = models.CharField(primary_key=True, max_length=100,
        error_messages={'unique': "This database name already exists."})
    database_title = models.CharField(max_length=200, blank=True)
    parse_seqids = models.BooleanField(blank=True)
    hash_index = models.BooleanField(blank=True)

    blastdb_version = models.CharField(
        max_length=12, choices=version, default="4")

    taxid = models.CharField(max_length=300, blank=True)
    taxid_map = models.FileField(upload_to='user_taxid_files/', blank=True)

    created = models.DateTimeField(editable=False, null=True)

    def filename(self):
        return os.path.basename(str(self.input_file))

    def print_type(self):
        if(self.database_type == "nucl"):
            return "Nucleotide"
        if(self.database_type == "prot"):
            return "Protein"

    def save(self, *args, **kwargs):
        # Overiding save method
        self.created = timezone.now()
        super().save(*args, **kwargs)
     

def user_input_presave(sender, instance, *args, **kwargs):
    # In case name_of_blast_db exists 
    if sender.objects.filter(name_of_blast_db = 
    instance.name_of_blast_db).exists():
        # Generate random index of 3 letters or numbers
        random_3 = string.ascii_letters.lower() + string.digits
        random.seed = (os.urandom(1024))
        random_id = "".join(random.choice(random_3) for i in range(3))
        new_name = instance.name_of_blast_db + "-" + str(random_id)

        # If this name still exists in model
        while sender.objects.filter(name_of_blast_db=new_name).exists():
            random_3 = string.ascii_letters.lower() + string.digits
            random.seed = (os.urandom(1024))
            random_id = "".join(random.choice(random_3) for i in range(3))
            new_name = instance.name_of_blast_db + "-" + str(random_id)

        # Insert new unique name    
        instance.name_of_blast_db = new_name
    
    # If database_title is not given
    if not instance.database_title:
        instance.database_title = instance.name_of_blast_db

pre_save.connect(user_input_presave, sender=UserInput)


class BlastDBData(models.Model):
    user_input = models.ForeignKey(UserInput, on_delete=models.CASCADE)
    father_database = models.ForeignKey('self', 
        on_delete=models.SET_NULL, 
        null=True, blank=True)
    zip_file = models.FileField()
    slug = models.SlugField(primary_key=True)


def blastdbdata_presave(sender, instance, *args, **kwargs):
    # Creating a slug for dynamic URL 
    if(instance.user_input):
        new_slug = slugify(instance.user_input.name_of_blast_db)
    # Checking if slug is unique in database table
    if sender.objects.filter(slug=new_slug).exists():
        random_3 = string.ascii_letters.lower() + string.digits
        random.seed = (os.urandom(1024))
        random_id = "".join(random.choice(random_3) for i in range(3))  
        new_slug = new_slug + "-" + str(random_id)
        while sender.objects.filter(slug=new_slug).exists():
            random_3 = string.ascii_letters.lower() + string.digits
            random.seed = (os.urandom(1024))
            random_id = "".join(random.choice(random_3) for i in range(3))  
            new_slug = new_slug + "-" + str(random_id)
        instance.slug = new_slug
    else:
        instance.slug = new_slug

pre_save.connect(blastdbdata_presave, sender=BlastDBData)


class BatchAlign(models.Model):
    DB_types = (
        ("nucl", "Nucleotide"),
        ("prot", "Protein"),
    )

    user_input = models.ForeignKey(UserInput, on_delete=models.CASCADE)
    database = models.ForeignKey(BlastDBData, on_delete=models.CASCADE)
    unique_db_index = models.SlugField(max_length=100)
    db_type = models.CharField(max_length=12, choices=DB_types)


class BLASTPlus(models.Model):
    sorting_hits_options = (
        ("0","Sort by evalue"),
        ("1","Sort by bit score"),
        ("2","Sort by total score"),
        ("3","Sort by percent identity"),
        ("4","Sort by query coverage"),
    )

    sorting_hsps_options = (
        ("0","Sort by hsp evalue"),
        ("1","Sort by hsp score"),
        ("2","Sort by hsp query start"),
        ("3","Sort by hsp percent identity"),
        ("4","Sort by hsp subject start"),
    )

    query_location = models.CharField(max_length=100, blank=True)
    output_filename = models.SlugField(max_length=100, primary_key=True, 
        error_messages ={"unique":"Provided output filename already exists."})
    
    # Optional/default arguments:
    evalue = models.FloatField(max_length=20, default=10)
    word_size = models.IntegerField(blank=True, null=True,
        validators=[
            MinValueValidator(2, message="Ensure word size is greater than \
            or equal to 2. "),
        ])
    
    ## Formatting options:
    show_gis = models.BooleanField(blank=True)
    line_length = models.IntegerField(default=60,
        validators=[
            MinValueValidator(1, message="Ensure line length is greater than \
                or equal to 1.")
        ])
    sort_hits = models.CharField(max_length=40, choices=sorting_hits_options,
        blank=True)
    sort_hsps = models.CharField(max_length=40, choices=sorting_hsps_options,
        blank=True)

    soft_masking = models.BooleanField(default=False)

    lcase_masking = models.BooleanField(blank=True)

    qcov_hsp_perc = models.FloatField(blank=True, null=True,
        validators=[
            MinValueValidator(0, message="Ensure percent query coverage  \
                per hsp is greater than or equal to 0."),
            MaxValueValidator(100, message="Ensure percent query coverage \
                per hsp is less than or equal to 100.")
        ])

    max_hsps = models.IntegerField(blank=True, null=True,
        validators=[
            MinValueValidator(1, message="Ensure maximum number of the HSPs \
                is greater than or equal to 1."),
        ])

    ## Restrict search or results:
    subject_besthit = models.BooleanField(blank=True)
    max_target_seqs = models.IntegerField(default=500,
        validators=[
            MinValueValidator(1, message="Ensure maximum number of aligned \
                sequences to keep is greater than or equal to 0."),
            MaxValueValidator(5000, message="Ensure maximum number of aligned \
                sequences to keep is less than or equal to 5000.")
        ])


    created = models.DateTimeField(editable=False, null=True)

    ## Miscellaneuous options:
    parse_deflines = models.BooleanField(blank=True)

    batch_align = models.ForeignKey(BatchAlign, on_delete=models.CASCADE, 
    blank=True, null=True)


    def save(self, *args, **kwargs):
        # Overiding save method
        self.created = timezone.now()
        super().save(*args, **kwargs)

    class Meta:
        abstract = True


class BlastnUserInput(BLASTPlus):
    strand_types = (
        ("both", "Both"),
        ("minus", "Minus"),
        ("plus", "Plus"),
    )

    task_types = (
        ("blastn", "BLASTn"),
        ("blastn-short", "BLASTn-short"),
        ("dc-megablast", "Dc-megaBLAST"),
        ("megablast", "MegaBLAST"),
    )

    database = models.ForeignKey(BlastDBData, on_delete=models.CASCADE, 
        related_name='blastndatabase', blank=True, null=True)
    
    query_file = models.FileField(upload_to='blastn_user_inputs/',
        validators=[FileExtensionValidator(allowed_extensions=['fasta'])])

    # Optional/default arguments:
    strand = models.CharField(max_length=12, choices=strand_types, 
        default="both")

    ## General search options:
    task = models.CharField(max_length=20, choices=task_types, 
        default="megablast")
    gap_open = models.IntegerField(blank=True, null=True)
    gap_extend = models.IntegerField(blank=True, null=True)
    reward = models.IntegerField(blank=True, null=True,
        validators=[
            MinValueValidator(0, message="Ensure reward for a nucleotide \
                match is greater than or equal to 0."),
        ])
    penalty = models.IntegerField(blank=True, null=True,
        validators=[
            MaxValueValidator(0, message="Ensure penalty for a nucleotide \
                mismatch is greater than or equal to 0.")
        ])

    ## Restrict search or results:
    gilist = models.FileField(upload_to=
        'blastn_inputs_parameters/', blank=True)
    seqidlist = models.FileField(upload_to=
        'blastn_inputs_parameters/', blank=True)
    negative_gilist = models.FileField(upload_to=
        'blastn_inputs_parameters/', blank=True)
    negative_seqidlist = models.FileField(upload_to=
        'blastn_inputs_parameters/', blank=True)
    taxids = models.CharField(max_length=200, blank=True, 
        validators=[
            validate_comma_separated_integer_list,
        ])
    negative_taxids = models.CharField(max_length=200, blank=True, 
        validators=[
            validate_comma_separated_integer_list,
        ])
    taxidlist = models.FileField(upload_to=
        'blastn_inputs_parameters/', blank=True)
    negative_taxidlist = models.FileField(upload_to=
        'blastn_inputs_parameters/', blank=True)
    perc_identity = models.FloatField(max_length=10, blank=True, null=True,
        validators=[
            MinValueValidator(0, message="Ensure percent identity is \
                greater than or equal to 0."),
            MaxValueValidator(100, message="Ensure percent identity is \
                less than or equal to 100.")
        ])


    def filename(self):
        return os.path.basename(str(self.query_file))
    

def blast_user_input_presave(sender, instance, *args, **kwargs):
    # if needed creating slug field for dynamic URL 
    new_slug = slugify(instance.output_filename)
    # cheking if slug is unique in database table
    if sender.objects.filter(output_filename=new_slug).exists():
        random_3 = string.ascii_letters.lower() + string.digits
        random.seed = (os.urandom(1024))
        random_id = "".join(random.choice(random_3) for i in range(3))
        new_slug = new_slug + "-" + str(random_id)
        while sender.objects.filter(output_filename=new_slug).exists():
            random_3 = string.ascii_letters.lower() + string.digits
            random.seed = (os.urandom(1024))
            random_id = "".join(random.choice(random_3) for i in range(3))
            new_slug = new_slug + "-" + str(random_id)
        instance.output_filename = new_slug
    else:
        instance.output_filename = new_slug  


pre_save.connect(blast_user_input_presave, sender=BlastnUserInput)


class BlastpUserInput(BLASTPlus):
    task_types = (
        ("blastp", "BLASTp"),
        ("blastp-fast", "BLASTp-fast"),
        ("blastp-short", "BLASTp-short"),
    )
    matrix_types = (
        ("PAM30", "PAM30"),
        ("PAM70", "PAM70"),
        ("BLOSUM80", "BLOSUM80"),
        ("BLOSUM62", "BLOSUM62"),
        ("BLOSUM50", "BLOSUM50"),
        ("BLOSUM45", "BLOSUM45"),
        ("PAM250", "PAM250"),
        ("BLOSUM90", "BLOSUM90"),
    )

    database = models.ForeignKey(BlastDBData, on_delete=models.CASCADE,
    related_name="blastpdatabase", blank=True, null=True)

    query_file = models.FileField(upload_to='blastp_user_inputs/',
        validators=[FileExtensionValidator(allowed_extensions=['fasta'])])

    # Optional/default arguments:
    task = models.CharField(max_length=20, choices=task_types, 
        default="blastp")
    gap_open = models.IntegerField(blank=True, null=True)
    gap_extend = models.IntegerField(blank=True, null=True)
    matrix = models.CharField(max_length=100, default="BLOSUM62", 
    choices=matrix_types)
    threshold = models.FloatField(max_length=10, blank=True, null=True,
        validators=[
            MinValueValidator(0, message="Ensure minimum word score is \
                greater than or equal to 0." )
        ])

    ## Restrict search or results
    gilist = models.FileField(upload_to=
        'blastp_inputs_parameters/', blank=True)
    seqidlist = models.FileField(upload_to=
        'blastp_inputs_parameters/', blank=True)
    negative_gilist = models.FileField(upload_to=
        'blastp_inputs_parameters/', blank=True)
    negative_seqidlist = models.FileField(upload_to=
        'blastp_inputs_parameters/', blank=True)
    taxids = models.CharField(max_length=200, blank=True, 
        validators=[
            validate_comma_separated_integer_list,
        ])
    negative_taxids = models.CharField(max_length=200, blank=True, 
        validators=[
            validate_comma_separated_integer_list,
        ])
    taxidlist = models.FileField(upload_to=
        'blastp_inputs_parameters/', blank=True)
    negative_taxidlist = models.FileField(upload_to=
        'blastp_inputs_parameters/', blank=True)


    def filename(self):
        return os.path.basename(str(self.query_file))

pre_save.connect(blast_user_input_presave, sender=BlastpUserInput)

class BlastxUserInput(BLASTPlus):
    strand_types = (
        ("both", "Both"),
        ("minus", "Minus"),
        ("plus", "Plus"),
    )
    
    task_types = (
        ("blastx", "BLASTx"),
        ("blastx-fast", "BLASTx-fast"),
    )

    matrix_types = (
        ("PAM30", "PAM30"),
        ("PAM70", "PAM70"),
        ("BLOSUM80", "BLOSUM80"),
        ("BLOSUM62", "BLOSUM62"),
        ("BLOSUM50", "BLOSUM50"),
        ("BLOSUM45", "BLOSUM45"),
        ("PAM250", "PAM250"),
        ("BLOSUM90", "BLOSUM90"),
    )

    database = models.ForeignKey(BlastDBData, on_delete=models.CASCADE,
    related_name="blastxdatabase", blank=True, null=True)

    query_file = models.FileField(upload_to='blastx_user_inputs/',
        validators=[FileExtensionValidator(allowed_extensions=['fasta'])])
    
    # Input query options:
    strand = models.CharField(max_length=12, choices=strand_types, 
        default="both")

    matrix = models.CharField(max_length=100, default="BLOSUM62", 
        choices=matrix_types)

    # General search options:
    task = models.CharField(max_length=20, choices=task_types, 
        default="blastx")
    gap_open = models.IntegerField(blank=True, null=True)
    gap_extend = models.IntegerField(blank=True, null=True)
    threshold = models.FloatField(max_length=10, blank=True, null=True,
        validators=[
            MinValueValidator(0, message="Ensure minimum word score is \
                greater than or equal to 0.")
        ])
    max_intron_length = models.IntegerField(default=0, 
    blank=True, null=True, validators=[
        MinValueValidator(0, message="Ensure length of the largest \
            intron allowed is greater than or equal to 0."),
    ])

    # Restrict search or results
    gilist = models.FileField(upload_to=
        'blastx_inputs_parameters/', blank=True)
    seqidlist = models.FileField(upload_to=
        'blastx_inputs_parameters/', blank=True)
    negative_gilist = models.FileField(upload_to=
        'blastx_inputs_parameters/', blank=True)
    negative_seqidlist = models.FileField(upload_to=
        'blastx_inputs_parameters/', blank=True)
    taxids = models.CharField(max_length=200, blank=True, 
        validators=[
            validate_comma_separated_integer_list
        ])
    negative_taxids = models.CharField(max_length=200, blank=True, 
        validators=[
            validate_comma_separated_integer_list
        ])
    taxidlist = models.FileField(upload_to=
        'blastx_inputs_parameters/', blank=True)
    negative_taxidlist = models.FileField(upload_to=
        'blastx_inputs_parameters/', blank=True)

    def filename(self):
        return os.path.basename(str(self.query_file))


pre_save.connect(blast_user_input_presave, sender=BlastxUserInput)


class tBlastxUserInput(BLASTPlus):
    strand_types = (
        ("both", "Both"),
        ("minus", "Minus"),
        ("plus", "Plus"),
    )

    matrix_types = (
        ("PAM30", "PAM30"),
        ("PAM70", "PAM70"),
        ("BLOSUM80", "BLOSUM80"),
        ("BLOSUM62", "BLOSUM62"),
        ("BLOSUM50", "BLOSUM50"),
        ("BLOSUM45", "BLOSUM45"),
        ("PAM250", "PAM250"),
        ("BLOSUM90", "BLOSUM90"),
    )

    database = models.ForeignKey(BlastDBData, on_delete=models.CASCADE,
    related_name="tblastxdatabase", blank=True, null=True)
    
    query_file = models.FileField(upload_to='tblastx_user_inputs/',
        validators=[FileExtensionValidator(allowed_extensions=['fasta'])])
    
    # Input query options:
    strand = models.CharField(max_length=12, choices=strand_types, 
        default="both")

    matrix = models.CharField(max_length=100, default="BLOSUM62", 
    choices=matrix_types)

    # General search options:
    threshold = models.FloatField(max_length=10, blank=True, null=True,
        validators=[
            MinValueValidator(0, message="Ensure minimum word score is \
                greater than or equal to 0.")
        ])

    # Restrict search or results
    gilist = models.FileField(upload_to=
        'tblastx_inputs_parameters/', blank=True)
    seqidlist = models.FileField(upload_to=
        'tblastx_inputs_parameters/', blank=True)
    negative_gilist = models.FileField(upload_to=
        'tblastx_inputs_parameters/', blank=True)
    negative_seqidlist = models.FileField(upload_to=
        'tblastx_inputs_parameters/', blank=True)
    taxids = models.CharField(max_length=200, blank=True, 
        validators=[
            validate_comma_separated_integer_list
        ])
    negative_taxids = models.CharField(max_length=200, blank=True, 
        validators=[
            validate_comma_separated_integer_list
        ])
    taxidlist = models.FileField(upload_to=
        'tblastx_inputs_parameters/', blank=True)
    negative_taxidlist = models.FileField(upload_to=
        'tblastx_inputs_parameters/', blank=True)

    def filename(self):
        return os.path.basename(str(self.query_file))

pre_save.connect(blast_user_input_presave, sender=tBlastxUserInput)

class tBlastnUserInput(BLASTPlus):
    task_types = (
        ("tblastn", "tBLASTn"),
        ("tblastn-fast", "tBLASTn-fast"),
    )

    database = models.ForeignKey(BlastDBData, on_delete=models.CASCADE,
    related_name="tblastndatabase", blank=True, null=True)

    query_file = models.FileField(upload_to='tblastn_user_inputs/',
        validators=[FileExtensionValidator(allowed_extensions=['fasta'])])
    
    # General search options:
    task = models.CharField(max_length=20, choices=task_types, 
        default="tblastn")
    gap_open = models.IntegerField(blank=True, null=True)
    gap_extend = models.IntegerField(blank=True, null=True)
    threshold = models.FloatField(max_length=10, blank=True, null=True,
        validators=[
            MinValueValidator(0, message="Ensure minimum word score is \
                greater than or equal to 0.")
        ])
    max_intron_length = models.IntegerField(default=0, 
    blank=True, null=True, validators=[
        MinValueValidator(0, message="Ensure length of the largest \
            intron allowed is greater than or equal to 0."),
    ])

    # Restrict search or results
    gilist = models.FileField(upload_to=
        'tblastn_inputs_parameters/', blank=True)
    seqidlist = models.FileField(upload_to=
        'tblastn_inputs_parameters/', blank=True)
    negative_gilist = models.FileField(upload_to=
        'tblastn_inputs_parameters/', blank=True)
    negative_seqidlist = models.FileField(upload_to=
        'tblastn_inputs_parameters/', blank=True)
    taxids = models.CharField(max_length=200, blank=True, 
        validators=[
            validate_comma_separated_integer_list
        ])
    negative_taxids = models.CharField(max_length=200, blank=True, 
        validators=[
            validate_comma_separated_integer_list
        ])
    taxidlist = models.FileField(upload_to=
        'tblastn_inputs_parameters/', blank=True)
    negative_taxidlist = models.FileField(upload_to=
        'tblastn_inputs_parameters/', blank=True)


    def filename(self):
        return os.path.basename(str(self.query_file))


pre_save.connect(blast_user_input_presave, sender=tBlastnUserInput)


class BlastnResults(models.Model):
    blastn_request = models.ForeignKey(BlastnUserInput, 
    on_delete=models.CASCADE)
    blastn_result = models.FileField()

class BlastpResults(models.Model):
    blastp_request = models.ForeignKey(BlastpUserInput, 
    on_delete=models.CASCADE)
    blastp_result = models.FileField()

class BlastxResults(models.Model):
    blastx_request = models.ForeignKey(BlastxUserInput, 
    on_delete=models.CASCADE)
    blastx_result = models.FileField()

class tBlastxResults(models.Model):
    tblastx_request = models.ForeignKey(tBlastxUserInput, 
    on_delete=models.CASCADE)
    tblastx_result = models.FileField()

class tBlastnResults(models.Model):
    tblastn_request = models.ForeignKey(tBlastnUserInput, 
    on_delete=models.CASCADE)
    tblastn_result = models.FileField()

class UpdateBlastDB(models.Model):
    user_input = models.ForeignKey(UserInput, on_delete=models.CASCADE,
        blank=True,
        null=True)
    database = models.ForeignKey(BlastDBData, on_delete=models.CASCADE, 
        blank=True, 
        null=True)
    updated_file_input = models.FileField(upload_to='blast_db_updates/', 
        blank=True)
    updated_file_text = models.TextField(max_length=300000, blank=True)
    update_alignments = models.BooleanField()
