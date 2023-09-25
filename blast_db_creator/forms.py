from django import forms
from django.forms import ModelForm
from .models import UserInput
from .models import BlastnUserInput
from .models import BlastpUserInput
from .models import UpdateBlastDB
from .models import tBlastnUserInput, tBlastxUserInput, BlastxUserInput
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.models import User
from django.contrib import messages
from django.forms import modelform_factory
import re


class CreateUserForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        # Inserting field names that will be present in the form
        fields = [
            'username',
            'email',
            'password1',
            'password2',
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].label = "Username:"
        self.fields['email'].label = "Email address:"
        self.fields['password1'].label = "Password:"
        self.fields['password2'].label = "Password confirmation:"

    def save(self, commit=True):
        user = super(CreateUserForm, self).save(commit=False)
        user.email = self.cleaned_data['email']
        if commit:
            user.save()
        return user


class LoginUserForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].label = "Username:"
        self.fields['password'].label = "Password:"


class CreateBlastDBFormPublic(ModelForm):
    class Meta:
        model = UserInput
        # Inserting field names that will be present in the form
        fields = [
            'public_or_private',
            'input_file',
            'database_type',
            'input_type',
            'name_of_blast_db',
            'database_title',
            'parse_seqids',
            'hash_index',
            'blastdb_version',
            'taxid',
            'taxid_map',
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['public_or_private'].widget = forms.HiddenInput()
        self.fields['public_or_private'].initial = 'public'
        self.fields['input_file'].label = "Insert a file (only .fasta \
            extension is allowed):"
        self.fields['database_type'].label = "Database type:"
        self.fields['input_type'].label = "File type:"
        self.fields['name_of_blast_db'].label = "Name of database:"
        self.fields['name_of_blast_db'].widget.attrs.update(
            {"placeholder":
                "Enter a value (numbers, lowercase letters, - and _)"}
        )
        self.fields['database_title'].label = "Title of database:"
        self.fields['database_title'].widget.attrs.update(
            {"placeholder":
            "Inserted name of database will be used, if not provided"})
        self.fields['parse_seqids'].label = "Keep the original sequence \
            identifiers"
        self.fields['hash_index'].label = "Create hash values"
        self.fields['blastdb_version'].label = "Version of BLAST \
            database to be created:"
        self.fields['taxid'].label = "Taxonomy ID:"
        self.fields['taxid'].widget.attrs.update(
            {"placeholder":
            "Insert a taxonomy ID (will be assigned to all sequences)"})
        self.fields['taxid_map'].label = "Taxonomy map:"


    def clean(self):
        super(CreateBlastDBFormPublic, self).clean()
        database_name = self.cleaned_data.get('name_of_blast_db')
        database_title = self.cleaned_data.get('database_title')


        if(database_name == database_title):
            match = validate_names(database_name)
            if match is not None:
                self._errors['name_of_blast_db'] = self.error_class([
                    'Database name and database title can only contain\
                    numbers, lower case letters, underscores or hyphens.'])
            else:
                is_usable_db_name = validate_start_char(database_name)
                if is_usable_db_name == False:
                    self._errors['name_of_blast_db'] = self.error_class([
                        'Database name and database title can only start\
                        with a letter.'])
        else:
            match = validate_names(database_name)
            if match is not None:
                self._errors['name_of_blast_db'] = self.error_class([
                    'Database name can only contain numbers, lower case\
                    letters, underscores or hyphens.'])
            else:
                is_usable_db_name = validate_start_char(database_name)
                if is_usable_db_name == False:
                    self._errors['name_of_blast_db'] = self.error_class([
                        'Database name can only start with a letter.'])

            match = validate_names(database_title)
            if match is not None:
                self._errors['database_title'] = self.error_class([
                    'Database title can only contain numbers, lower case\
                    letters, underscores or hyphens.'])
            else:
                is_usable_db_title = validate_start_char(database_title)
                if is_usable_db_title == False:
                    self._errors['database_title'] = self.error_class([
                        'Database title can only start with a letter.'])

        return self.cleaned_data


class CreateBlastDBFormUser(ModelForm):
    class Meta:
        model = UserInput
        # Inserting field names that will be present in the form
        fields = [
            'public_or_private',
            'input_file',
            'database_type',
            'input_type',
            'name_of_blast_db',
            'database_title',
            'parse_seqids',
            'hash_index',
            'blastdb_version',
            'taxid',
            'taxid_map',
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['public_or_private'].label = "Database:"
        self.fields['input_file'].label = "Insert a file (only .fasta \
            extension is allowed):"
        self.fields['database_type'].label = "Database type:"
        self.fields['input_type'].label = "File type:"
        self.fields['name_of_blast_db'].label = "Name of the database:"
        self.fields['name_of_blast_db'].widget.attrs.update(
            {"placeholder":
                "Enter a value (numbers, lowercase letters, - and _)"}
        )
        self.fields['database_title'].label = "Title of the database:"
        self.fields['database_title'].widget.attrs.update(
            {"placeholder":
            "Inserted name of database will be used, if not provided"})
        self.fields['parse_seqids'].label = "Enable sequence ID parsing"
        self.fields['hash_index'].label = "Create hash values"
        self.fields['blastdb_version'].label = "Version of BLAST \
            database to be created:"
        self.fields['taxid'].label = "Taxonomy ID:"
        self.fields['taxid'].widget.attrs.update(
            {"placeholder":
            "Insert a taxonomy ID (will be assigned to all sequences)"})
        self.fields['taxid_map'].label = "Taxonomy map:"

    def clean(self):
        super(CreateBlastDBFormUser, self).clean()
        database_name = self.cleaned_data.get('name_of_blast_db')
        database_title = self.cleaned_data.get('database_title')

        if(database_name == database_title):
            match = validate_names(database_name)
            if match is not None:
                self._errors['name_of_blast_db'] = self.error_class([
                    'Database name and database title can only contain\
                    numbers, lower case letters, underscores or hyphens.'])
            else:
                is_usable_db_name = validate_start_char(database_name)
                if is_usable_db_name == False:
                    self._errors['name_of_blast_db'] = self.error_class([
                        'Database name and database title can only start\
                        with a letter.'])
        else:
            match = validate_names(database_name)
            if match is not None:
                self._errors['name_of_blast_db'] = self.error_class([
                    'Database name can only contain numbers, lower case\
                    letters, underscores or hyphens.'])
            else:
                is_usable_db_name = validate_start_char(database_name)
                if is_usable_db_name == False:
                    self._errors['name_of_blast_db'] = self.error_class([
                        'Database name can only start with a letter.'])

            match = validate_names(database_title)
            if match is not None:
                self._errors['database_title'] = self.error_class([
                    'Database title can only contain numbers, lower case\
                    letters, underscores or hyphens.'])
            else:
                is_usable_db_title = validate_start_char(database_title)
                if is_usable_db_title == False:
                    self._errors['database_title'] = self.error_class([
                        'Database title can only start with a letter.'])

        return self.cleaned_data


def validate_start_char(name):
    if name.startswith('-') or name.startswith('_') or re.match(r"^\d", name):
        return False

def validate_names(name):
    invalid_chars = '[\@!#$%^&*()<>?/\|}{~:"\'.,\[\]\sA-Z]'
    match = re.search(invalid_chars, name)
    return match


class BlastnForm(ModelForm):
    output_filename = forms.SlugField(error_messages={'invalid':'Output \
        filename can only contain numbers, letters, underscores or hyphens.'})
    class Meta:
        model = BlastnUserInput
        # Inserting field names that will be present in the form
        fields = [
            'query_file',
            'output_filename',
            'query_location',
            'strand',
            'task',
            'evalue',
            'word_size',
            'gap_open',
            'gap_extend',
            'reward',
            'penalty',
            'show_gis',
            'line_length',
            'sort_hits',
            'sort_hsps',
            'soft_masking',
            'lcase_masking',
            'gilist',
            'seqidlist',
            'negative_gilist',
            'negative_seqidlist',
            'taxids',
            'negative_taxids',
            'taxidlist',
            'negative_taxidlist',
            'perc_identity',
            'qcov_hsp_perc',
            'max_hsps',
            'subject_besthit',
            'max_target_seqs',
            'parse_deflines',
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['query_file'].label = "Insert nucleotide query  \
            file (only .fasta extension is allowed):"
        self.fields['output_filename'].label = "Insert output filename:"
        self.fields['output_filename'].widget.attrs.update(
            {"placeholder":"Enter a value (numbers, lowercase letters, _, -) without file extension"})
        self.fields['query_location'].label = "Location on the query sequence:"
        self.fields['query_location'].widget.attrs.update(
            {"placeholder":"Format: start-stop, e.g. 1-33"})
        self.fields['strand'].label = "Query strand(s) to search against \
            database:"
        self.fields['task'].label = "Task to execute:"
        self.fields['evalue'].label = "Expectation value (E) threshold \
            for saving hits:"
        self.fields['word_size'].label = "Word size:"
        self.fields['gap_open'].label = "Cost to open a gap:"
        self.fields['gap_extend'].label = "Cost to extend a gap:"
        self.fields['penalty'].label = "Penalty for a nucleotide mismatch:"
        self.fields['reward'].label = "Reward for a nucleotide match:"
        self.fields['show_gis'].label = "Show NCBI GIs in deflines"
        self.fields['line_length'].label = "Line length for formatting \
            alignments:"
        self.fields['sort_hits'].label = "Sorting option for the hits:"
        self.fields['sort_hsps'].label = "Sorting option for the hps:"
        self.fields['soft_masking'].label = "Apply filtering locations \
            as soft masks"
        self.fields['lcase_masking'].label = "Use lower case filtering \
            in query and subject sequence(s)"
        self.fields['gilist'].label = "Insert file of the GIs to use:"
        self.fields['seqidlist'].label = "Insert a file of the SeqIDs to use:"
        self.fields['negative_gilist'].label = "Insert a file of GIs which \
            must not be used:"
        self.fields['negative_seqidlist'].label = "Insert a file of SeqIDs \
            which must not be used: "
        self.fields['taxids'].label = "Taxonomy IDs to use in search of \
            database:"
        self.fields['taxids'].widget.attrs.update(
            {"placeholder":"Delimit multiple IDs by \',\'"})
        self.fields['negative_taxids'].label = "Taxonomy IDs which must not \
            be included in search:"
        self.fields['negative_taxids'].widget.attrs.update(
            {"placeholder":"Delimit multiple IDs by \',\'"})
        self.fields['taxidlist'].label = "Insert a file of taxonomy IDs \
             to use in search of database:"
        self.fields['negative_taxidlist'].label = "Insert a file of taxonomy \
             IDs which must not be included in search:"
        self.fields['perc_identity'].label = "Percent identity:"
        self.fields['qcov_hsp_perc'].label = "Percent query coverage per hsp:"
        self.fields['max_hsps'].label = "Maximum number of the HSPs per \
            subject sequence to save for each query:"
        self.fields['subject_besthit'].label = "Turn on best hit per \
            subject sequence"
        self.fields['max_target_seqs'].label = "Maximum number of aligned \
            sequences to keep:"
        self.fields['parse_deflines'].label = "Parse query and subject bar \
            delimited sequence identifiers"
  
    def clean(self):
        super(BlastnForm, self).clean()
        output_filename = self.cleaned_data.get('output_filename')

        is_usable_db_name = validate_start_char(str(output_filename))
        if is_usable_db_name == False:
            self._errors['output_filename'] = self.error_class([
                'Output filename can only start with a letter.'])
        
        return self.cleaned_data


class BlastpForm(ModelForm):
    output_filename = forms.SlugField(error_messages={'invalid':'Output \
        filename can only contain numbers, letters, underscores or hyphens.'})

    class Meta:
        model = BlastpUserInput
        # Inserting field names that will be present in the form
        fields = [
            'query_file',
            'output_filename',
            'query_location',
            'task',
            'evalue',
            'word_size',
            'gap_open',
            'gap_extend',
            'matrix',
            'threshold',
            'show_gis',
            'line_length',
            'sort_hits',
            'sort_hsps',
            'soft_masking',
            'lcase_masking',
            'gilist',
            'seqidlist',
            'negative_gilist',
            'negative_seqidlist',
            'taxids',
            'negative_taxids',
            'taxidlist',
            'negative_taxidlist',
            'qcov_hsp_perc',
            'max_hsps',
            'subject_besthit',
            'max_target_seqs',
            'parse_deflines',
       ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['query_file'].label = "Insert protein query file  \
        (only .fasta extension is allowed):"
        self.fields['output_filename'].label = "Insert output filename:"
        self.fields['output_filename'].widget.attrs.update(
            {"placeholder":
            "Enter a value (numbers, lowercase letters, _, -) without file extension"})
        self.fields['query_location'].label = "Location on the query sequence:"
        self.fields['query_location'].widget.attrs.update(
            {"placeholder":"Format: start-stop, e.g. 1-33"})
        self.fields['task'].label = "Task to execute:"
        self.fields['evalue'].label = "Expectation value (E) \
            threshold for saving hits:"
        self.fields['word_size'].label = "Word size:"
        self.fields['gap_open'].label = "Cost to open a gap:"
        self.fields['gap_extend'].label = "Cost to extend a gap:"
        self.fields['matrix'].label = "Scoring matrix name:"
        self.fields['threshold'].label = "Minimum word score such that \
            the word is added to the BLAST lookup table:"
        self.fields['show_gis'].label = "Show NCBI GIs in deflines"
        self.fields['line_length'].label = "Line length for formatting \
            alignments:"
        self.fields['sort_hits'].label = "Sorting option for hits:"
        self.fields['sort_hsps'].label = "Sorting option for hps:"
        self.fields['soft_masking'].label = "Apply filtering locations \
             as soft masks"
        self.fields['lcase_masking'].label = "Use lower case filtering in \
            query and subject sequence(s)"
        self.fields['gilist'].label = "Insert file of GIs to use:"
        self.fields['seqidlist'].label = "Insert file of SeqIDs to use:"
        self.fields['negative_gilist'].label = "Insert file of GIs which \
            must not be used:"
        self.fields['negative_seqidlist'].label = "Insert file of SeqIDs \
            which must not be used:"
        self.fields['taxids'].label = "Taxonomy IDs to use in search of \
            database:"
        self.fields['taxids'].widget.attrs.update(
            {"placeholder":"Delimit multiple IDs by \',\'"})
        self.fields['negative_taxids'].label = "Taxonomy IDs which must not \
            be included in search:"
        self.fields['negative_taxids'].widget.attrs.update(
            {"placeholder":"Delimit multiple IDs by \',\'"})
        self.fields['taxidlist'].label = "Insert file of taxonomy IDs \
             to use in search of database:"
        self.fields['negative_taxidlist'].label = "Insert file of taxonomy \
             IDs which must not be included in search:"
        self.fields['qcov_hsp_perc'].label = "Percent query coverage per hsp:"
        self.fields['max_hsps'].label = "Maximum number of HSPs per \
            subject sequence to save for each query:"
        self.fields['subject_besthit'].label = "Turn on best hit per subject \
            sequence"
        self.fields['max_target_seqs'].label = "Maximum number of aligned \
            sequences to keep:"
        self.fields['parse_deflines'].label = "Parse query and subject bar \
            delimited sequence identifiers"

    def clean(self):
        super(BlastpForm, self).clean()
        output_filename = self.cleaned_data.get('output_filename')

        is_usable_db_name = validate_start_char(str(output_filename))
        if is_usable_db_name == False:
            self._errors['output_filename'] = self.error_class([
                'Output filename can only start with a letter.'])
        
        return self.cleaned_data


def validate_update_data(data):
    invalid_chars = '[\@!#$%^&*<?\}{~"\']'
    match = re.search(invalid_chars, data)
    return match


class UpdateBlastDBForm(ModelForm):
    class Meta:
        model = UpdateBlastDB
        fields = [
            'updated_file_input',
            'updated_file_text',
            'update_alignments',
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['updated_file_input'].label = "Insert an updated file:"
        self.fields['updated_file_text'].label = "Paste in the updated file \
            (FASTA file format, up to 1 MB):"
        self.fields['update_alignments'].label = "Do you want to reload \
            existing alignments? (It may take a long time)"

    def clean(self):
        super(UpdateBlastDBForm, self).clean()
        updated_file_text = self.cleaned_data.get('updated_file_text')
        updated_file_input = self.cleaned_data.get('updated_file_input')

        if not updated_file_input and not updated_file_text:
            raise forms.ValidationError(
                "Please insert either updated file or \
                    paste in the file content."
        )


        if(updated_file_text):
            match = validate_update_data(str(updated_file_text))
            if match is not None:
                self._errors['updated_file_text'] = \
                self.error_class(['Uploaded content contains forbidden' + 
                ' letters. Please correct the content or paste in new content.']
                )

        return self.cleaned_data

class BlastxForm(ModelForm):
    output_filename = forms.SlugField(error_messages={'invalid':'Output \
        filename can only contain numbers, letters, underscores or hyphens.'})

    class Meta:
        model = BlastxUserInput
        # Inserting field names that will be present in the form
        fields = [
            'query_file',
            'output_filename',
            'query_location',
            'strand',
            'max_intron_length',
            'task',
            'matrix',
            'evalue',
            'word_size',
            'gap_open',
            'gap_extend',
            'threshold',
            'show_gis',
            'line_length',
            'sort_hits',
            'sort_hsps',
            'soft_masking',
            'lcase_masking',
            'gilist',
            'seqidlist',
            'negative_gilist',
            'negative_seqidlist',
            'taxids',
            'negative_taxids',
            'taxidlist',
            'negative_taxidlist',
            'qcov_hsp_perc',
            'max_hsps',
            'subject_besthit',
            'max_target_seqs',
            'parse_deflines',
       ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['query_file'].label = "Insert nucleotide query file  \
        (only .fasta extension is allowed):"
        self.fields['output_filename'].label = "Insert output filename:"
        self.fields['output_filename'].widget.attrs.update(
            {"placeholder":
                "Enter a value (numbers, lowercase letters, _, -) without file extension"})
        self.fields['query_location'].label = "Location on the query sequence:"
        self.fields['query_location'].widget.attrs.update(
            {"placeholder":"Format: start-stop, e.g. 1-33"})
        self.fields['strand'].label = "Query strand(s) to search against \
            database:"
        self.fields['matrix'].label = "Scoring matrix name:"
        self.fields['max_intron_length'].label = "Length of the largest intron \
            allowed in a translated nucleotide sequence:"
        self.fields['task'].label = "Task to execute:"
        self.fields['evalue'].label = "Expectation value (E) \
            threshold for saving hits:"
        self.fields['word_size'].label = "Word size:"
        self.fields['gap_open'].label = "Cost to open a gap:"
        self.fields['gap_extend'].label = "Cost to extend a gap:"
        self.fields['threshold'].label = "Minimum word score such that \
            the word is added to the BLAST lookup table:"
        self.fields['show_gis'].label = "Show NCBI GIs in deflines"
        self.fields['line_length'].label = "Line length for formatting \
            alignments:"
        self.fields['sort_hits'].label = "Sorting option for hits:"
        self.fields['sort_hsps'].label = "Sorting option for hps:"
        self.fields['soft_masking'].label = "Apply filtering locations \
             as soft masks"
        self.fields['lcase_masking'].label = "Use lower case filtering in \
            query and subject sequence(s)"
        self.fields['gilist'].label = "Insert file of GIs to use:"
        self.fields['seqidlist'].label = "Insert file of SeqIDs to use:"
        self.fields['negative_gilist'].label = "Insert file of GIs which \
            must not be used:"
        self.fields['negative_seqidlist'].label = "Insert file of SeqIDs \
            which must not be used:"
        self.fields['taxids'].label = "Taxonomy IDs to use in search of \
            database:"
        self.fields['taxids'].widget.attrs.update(
            {"placeholder":"Delimit multiple IDs by \',\'"})
        self.fields['negative_taxids'].label = "Taxonomy IDs which must not \
            be included in search:"
        self.fields['negative_taxids'].widget.attrs.update(
            {"placeholder":"Delimit multiple IDs by \',\'"})
        self.fields['taxidlist'].label = "Insert file of taxonomy IDs \
             to use in search of database:"
        self.fields['negative_taxidlist'].label = "Insert file of taxonomy \
             IDs which must not be included in search:"
        self.fields['qcov_hsp_perc'].label = "Percent query coverage per hsp:"
        self.fields['max_hsps'].label = "Maximum number of HSPs per \
            subject sequence to save for each query:"
        self.fields['subject_besthit'].label = "Turn on best hit per subject \
            sequence"
        self.fields['max_target_seqs'].label = "Maximum number of aligned \
            sequences to keep:"
        self.fields['parse_deflines'].label = "Parse query and subject bar \
            delimited sequence identifiers"

    def clean(self):
        super(BlastxForm, self).clean()
        output_filename = self.cleaned_data.get('output_filename')

        is_usable_db_name = validate_start_char(str(output_filename))
        if is_usable_db_name == False:
            self._errors['output_filename'] = self.error_class([
                'Output filename can only start with a letter.'])
        
        return self.cleaned_data



class tBlastxForm(ModelForm):
    output_filename = forms.SlugField(error_messages={'invalid':'Output \
        filename can only contain numbers, letters, underscores or hyphens.'})

    class Meta:
        model = tBlastxUserInput
        # Inserting field names that will be present in the form
        fields = [
            'query_file',
            'output_filename',
            'query_location',
            'strand',
            'matrix',
            'evalue',
            'word_size',
            'threshold',
            'show_gis',
            'line_length',
            'sort_hits',
            'sort_hsps',
            'soft_masking',
            'lcase_masking',
            'gilist',
            'seqidlist',
            'negative_gilist',
            'negative_seqidlist',
            'taxids',
            'negative_taxids',
            'taxidlist',
            'negative_taxidlist',
            'qcov_hsp_perc',
            'max_hsps',
            'max_target_seqs',
            'subject_besthit',
            'parse_deflines',
       ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['query_file'].label = "Insert nucleotide query file  \
        (only .fasta extension is allowed):"
        self.fields['output_filename'].label = "Insert output filename:"
        self.fields['output_filename'].widget.attrs.update(
            {"placeholder":"Enter a value (numbers, lowercase letters, _, -) without file extension"})
        self.fields['query_location'].label = "Location on the query sequence:"
        self.fields['query_location'].widget.attrs.update(
            {"placeholder":"Format: start-stop, e.g. 1-33"})
        self.fields['strand'].label = "Query strand(s) to search against \
            database:"
        self.fields['matrix'].label = "Scoring matrix name:"
        self.fields['evalue'].label = "Expectation value (E) \
            threshold for saving hits:"
        self.fields['word_size'].label = "Word size:"
        self.fields['threshold'].label = "Minimum word score such that \
            the word is added to the BLAST lookup table:"
        self.fields['show_gis'].label = "Show NCBI GIs in deflines"
        self.fields['line_length'].label = "Line length for formatting \
            alignments:"
        self.fields['sort_hits'].label = "Sorting option for hits:"
        self.fields['sort_hsps'].label = "Sorting option for hps:"
        self.fields['soft_masking'].label = "Apply filtering locations \
             as soft masks"
        self.fields['lcase_masking'].label = "Use lower case filtering in \
            query and subject sequence(s)"
        self.fields['gilist'].label = "Insert file of GIs to use:"
        self.fields['seqidlist'].label = "Insert file of SeqIDs to use:"
        self.fields['negative_gilist'].label = "Insert file of GIs which \
            must not be used:"
        self.fields['negative_seqidlist'].label = "Insert file of SeqIDs \
            which must not be used:"
        self.fields['taxids'].label = "Taxonomy IDs to use in search of \
            database:"
        self.fields['taxids'].widget.attrs.update(
            {"placeholder":"Delimit multiple IDs by \',\'"})
        self.fields['negative_taxids'].label = "Taxonomy IDs which must not \
            be included in search:"
        self.fields['negative_taxids'].widget.attrs.update(
            {"placeholder":"Delimit multiple IDs by \',\'"})
        self.fields['taxidlist'].label = "Insert file of taxonomy IDs \
             to use in search of database:"
        self.fields['negative_taxidlist'].label = "Insert file of taxonomy \
             IDs which must not be included in search:"
        self.fields['qcov_hsp_perc'].label = "Percent query coverage per hsp:"
        self.fields['max_hsps'].label = "Maximum number of HSPs per \
            subject sequence to save for each query:"
        self.fields['subject_besthit'].label = "Turn on best hit per subject \
            sequence"
        self.fields['max_target_seqs'].label = "Maximum number of aligned \
            sequences to keep:"
        self.fields['parse_deflines'].label = "Parse query and subject bar \
            delimited sequence identifiers"

    def clean(self):
        super(tBlastxForm, self).clean()
        output_filename = self.cleaned_data.get('output_filename')

        is_usable_db_name = validate_start_char(str(output_filename))
        if is_usable_db_name == False:
            self._errors['output_filename'] = self.error_class([
                'Output filename can only start with a letter.'])
        
        return self.cleaned_data


class tBlastnForm(ModelForm):
    output_filename = forms.SlugField(error_messages={'invalid':'Output \
        filename can only contain numbers, letters, underscores or hyphens.'})

    class Meta:
        model = tBlastnUserInput
        # Inserting field names that will be present in the form
        fields = [
            'query_file',
            'output_filename',
            'query_location',
            'task',
            'max_intron_length',
            'evalue',
            'word_size',
            'gap_open',
            'gap_extend',
            'threshold',
            'show_gis',
            'line_length',
            'sort_hits',
            'sort_hsps',
            'soft_masking',
            'lcase_masking',
            'gilist',
            'seqidlist',
            'negative_gilist',
            'negative_seqidlist',
            'taxids',
            'negative_taxids',
            'taxidlist',
            'negative_taxidlist',
            'qcov_hsp_perc',
            'max_hsps',
            'subject_besthit',
            'max_target_seqs',
            'parse_deflines',
       ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['query_file'].label = "Insert protein query file  \
        (only .fasta extension is allowed):"
        self.fields['output_filename'].label = "Insert output filename:"
        self.fields['output_filename'].widget.attrs.update(
            {"placeholder":"Enter a value (numbers, lowercase letters, _, -) without file extension"})
        self.fields['query_location'].label = "Location on the query sequence:"
        self.fields['query_location'].widget.attrs.update(
            {"placeholder":"Format: start-stop, e.g. 1-33"})
        self.fields['task'].label = "Task to execute:"
        self.fields['max_intron_length'].label = "Length of the largest intron \
            allowed in a translated nucleotide sequence:"
        self.fields['evalue'].label = "Expectation value (E) \
            threshold for saving hits:"
        self.fields['word_size'].label = "Word size:"
        self.fields['gap_open'].label = "Cost to open a gap:"
        self.fields['gap_extend'].label = "Cost to extend a gap:"
        self.fields['threshold'].label = "Minimum word score such that \
            the word is added to the BLAST lookup table:"
        self.fields['show_gis'].label = "Show NCBI GIs in deflines"
        self.fields['line_length'].label = "Line length for formatting \
            alignments:"
        self.fields['sort_hits'].label = "Sorting option for hits:"
        self.fields['sort_hsps'].label = "Sorting option for hps:"
        self.fields['soft_masking'].label = "Apply filtering locations \
             as soft masks"
        self.fields['lcase_masking'].label = "Use lower case filtering in \
            query and subject sequence(s)"
        self.fields['gilist'].label = "Insert file of GIs to use:"
        self.fields['seqidlist'].label = "Insert file of SeqIDs to use:"
        self.fields['negative_gilist'].label = "Insert file of GIs which \
            must not be used:"
        self.fields['negative_seqidlist'].label = "Insert file of SeqIDs \
            which must not be used:"
        self.fields['taxids'].label = "Taxonomy IDs to use in search of \
            database:"
        self.fields['taxids'].widget.attrs.update(
            {"placeholder":"Delimit multiple IDs by \',\'"})
        self.fields['negative_taxids'].label = "Taxonomy IDs which must not \
            be included in search:"
        self.fields['negative_taxids'].widget.attrs.update(
            {"placeholder":"Delimit multiple IDs by \',\'"})
        self.fields['taxidlist'].label = "Insert file of taxonomy IDs \
             to use in search of database:"
        self.fields['negative_taxidlist'].label = "Insert file of taxonomy \
             IDs which must not be included in search:"
        self.fields['qcov_hsp_perc'].label = "Percent query coverage per hsp:"
        self.fields['max_hsps'].label = "Maximum number of HSPs per \
            subject sequence to save for each query:"
        self.fields['subject_besthit'].label = "Turn on best hit per subject \
            sequence"
        self.fields['max_target_seqs'].label = "Maximum number of aligned \
            sequences to keep:"
        self.fields['parse_deflines'].label = "Parse query and subject bar \
            delimited sequence identifiers"

    def clean(self):
        super(tBlastnForm, self).clean()
        output_filename = self.cleaned_data.get('output_filename')

        is_usable_db_name = validate_start_char(str(output_filename))
        if is_usable_db_name == False:
            self._errors['output_filename'] = self.error_class([
                'Output filename can only start with a letter.'])
        
        return self.cleaned_data
