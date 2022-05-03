# Introduction to the Labbook!
Here we give an introduction how to use the lab book. For more details on the concept see our paper at https://arxiv.org/abs/2205.01058

install Docker and run

    docker-compose up

go to
    http://127.0.0.1:8000/

![Experiments](https://github.com/ag-gipp/Electronic-Laboratory-Notebook/blob/master/Readme_img/Experiments.png)

To see all the main experiments go to Experiments.
For details of the experiments select the experiment in the dropdown.

![Details of entry](https://github.com/ag-gipp/Electronic-Laboratory-Notebook/blob/master/Readme_img/Details.png)

I you want to see details on a single entry click on the eye.
In the popup windows further details can be displayed or links to the according plots are shown.

# Add new file to exsisting model and sample

If we want to add a new file to the lab book we can simply add it by copying it to the folder structure.
One example file is already present in this commit.
The file is saved at 01_Data\01_Main_Exp\01_OCA_35_XL\20210201\Probe_BA_01\171700_osz_wasser_laengest.png
From this path the program the information that the measurement was recorded at the first of february at 17:17:00 and the sample BA_01 was used in the experiment OCA.
The file will be ignored if it is older than 5 days or has the wrong file ending.
To add the change the folder name of the date to yesterday.
Navigate to Generate and click on Generate entries.
When going back to the experiments there should be a new entry with a different image then the other OCA_Exp entry.
If you have files that do not have the time written in front of them, consider using the give_file_times module in Exp_Main/Generate.py

# Add a new sample

To add a new sample navigate to http://127.0.0.1:8000/admin/ and low in the username: admin and password: admin
Go to Lab_Misc and click on samplebrushpnipaamsi and then add.
Important now is to give a proper name consistent of two letters and two numbers which are separated by an underscore.
Click save.
Now you can use this name in the folder structure and add a sample like described above.
It is probably useful to define your own model for your sample which inherits Sample_Blanks.
For further details about models visit https://docs.djangoproject.com/en/3.1/topics/db/models/

# Add a new experiment
To add a new experiment navigate to Exp_Main/models.py and add your model which inherits ExpBase.
For the start you can orient on the OCA model.
The model name should consist of 3 capital letters.
After the migration the model should be visible in the admin.
To tell the program where the files of this model are stored navigate in the admin to Exp path and create a new entry with the path file ending and the abbreviation witch consists of the same 3 capital letters as in the model.


If you use a windows system it can be beneficial to run django without docker, since only with windows it is possible to open local files directly from the browser.
If installed natively you can create a environment variable 'Experimental' and set it to your data directory.
In case you want to use a customized Labbook version you can create a environment variable 'DJANGO_SETTINGS_MODULE' to set the ralativ path to your customized 'manage.py'.
