# BLAST Databases

BLAST Databases is a biological internet application built on the foundation of the powerful BLAST+ command line application suite and the Django framework. It empowers users to create local BLAST databases and search for alignments, all without the need for manual command-line operations.

# Environment requirements
The biological application is designed and optimized to run on Unix-based operating systems.
To ensure successful execution, please ensure that the following prerequisites are met:
- Python, pip, and virtualenv must be installed on the system.
- BLAST Databases application supports Python versions 3.8, 3.9, 3.10, and 3.11.


## Installation
To set up the BLAST Databases application, follow the steps below:

1. Open the terminal and navigate to the directory where you wish to store the project.
Execute the following command:

```bash
git clone https://github.com/luksaiterugile/Thesis-BLAST-Databases.git
```

2. Enter the repository directory and install the required packages by executing the following command:
```bash
./install_packages.sh
```

2. After the installation process, create a virtual environment and activate it using the following commands:
```bash
python -V
python<version> -m venv BLAST_Databases
source BLAST_Databases/bin/activate
```

3. Once the virtual environment is activated, install the necessary Python packages by running:
```bash
pip install -r requirements.txt
```

4. Open two additional terminal windows and activate the virtual environment in each of them as described in step 2 (3rd command). At this point, you should have three terminal windows open, all with the virtual environment activated.

5. In the first terminal window, initiate the Redis server by executing:
```bash
redis-server
```

6. In the second terminal window, start the Celery system by running:
```bash
celery -A my_project worker -l info
```

7. In the third terminal window, perform the Django project migration by executing:
```bash
python manage.py migrate
```

6. Finally, launch the BLAST Databases application by running:
```bash
python manage.py runserver
```

### Creating a superuser
To create a superuser for administrative access, execute the following command before starting the Django server:
```bash
python manage.py createsuperuser
```

By following these instructions, you'll be able to set up the BLAST Databases application.
