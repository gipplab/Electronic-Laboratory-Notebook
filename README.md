# Introduction to the Labbook!


With this lab book, you can **store, organize, and analyze** the experiments you've performed. It is designed for **individual users** with a **large number of experiments**. You can **input the data** you receive from your experiments and **automatically store it in a database**, which allows you to **categorize the data** in a way that suits your needs. Additionally, you can **access the database** using **Jupyter Notebook** and **manipulate it** as needed. Within the Jupyter Notebook, you also have access to all the functions that you've defined in your **Django framework**.

![Experiments](https://github.com/ag-gipp/Electronic-Laboratory-Notebook/blob/master/Readme_img/scheme.png)

## Used in references

So far, we have used the lab book in the following scientific papers:

- [ACS Langmuir](https://doi.org/10.1021/acs.langmuir.2c03009)
- [J. Colloid Interface Sci.](https://doi.org/10.1016/j.jcis.2023.03.139)

## How It Works

In essence, we recorded videos and loaded them into our database, connecting the video files to all the details of the experiment, such as information about the sample, the liquid used, or the atmospheric conditions during the experiment. From within the lab book, we started the analysis, which allowed us to save analysis parameters for potential reruns. The results of this analysis were also stored in the lab book, enabling us to perform a meta-analysis of these results using the Jupyter Notebook.

For more details on the concept see our [paper](https://arxiv.org/abs/2205.01058).


# Getting Started with Docker

1. **Run the App in Docker**:
   - Open your terminal or command prompt.
   - Navigate to the root directory of your project.
   - Type the following command to start the app in Docker: `docker-compose up`
   - Open your web browser and visit http://127.0.0.1:8000/

This command will build and run the necessary containers defined in your `docker-compose.yml` file.

That's it! You're now ready to explore the lab book within a Docker environment.


# Exploring the Lab Book

We'll cover how to explore experiments, group them, focus on specific experiments, visualize data, connect data sources, and add new experiments.

## 1. Exploring Experiments
- Click on the **"Experiments"** section to find a list of various experiments.
- For details of the experiments select the experiment in the dropdown.

![Experiments](https://github.com/ag-gipp/Electronic-Laboratory-Notebook/blob/master/Readme_img/Experiments.png)

- When you click on the eye icon next to an experiment, you'll see additional details. For example, in the SFG experiments, you'll find information about the type of polarization used during each experiment or links to the according plots are shown.

![Details of entry](https://github.com/ag-gipp/Electronic-Laboratory-Notebook/blob/master/Readme_img/Details.png)

## 2. Grouping Experiments
- You have the option to group several experiments together. This grouping can be done manually or based on the folder structure.
- Grouping experiments allows you to analyze them collectively, which can be helpful for drawing insights.

## 3. Focus on a Specific Experiment
- Let's focus on a specific experiment that was performed in this research paper: Link to Research Paper
- In this experiment, we recorded a drop and analyzed a video to extract the contact angle. The contact angle data is saved in a text file.

## 4. Visualizing Data
- Click on the eye of the **OCA experiment (AA_01_OCA-200)**.
- You'll notice an option to view a plot (Link to plot). However, the default representation of contact angle over time may not be ideal for our needs.

![Experiments](https://github.com/ag-gipp/Electronic-Laboratory-Notebook/blob/master/Readme_img/CA_time.png)

## 5. Connecting Data Sources
- To address this, we connected the contact angle data from the OCA experiment to the data obtained from the syringe pump.
- Click on **Flowrate / Time** to visualize both files over time: the contact angle data and the flow rate of the pump.

![Experiments](https://github.com/ag-gipp/Electronic-Laboratory-Notebook/blob/master/Readme_img/Flow_CA.png)

- There is a small offset between the flow and the contact angle. This can be corrected by shifting them. Therfor click on the pencil and enter 20 seconds as the the shift.

![Experiments](https://github.com/ag-gipp/Electronic-Laboratory-Notebook/blob/master/Readme_img/shift_flow.png)

## 6. Distinguishing Drops
- Now, if you click on **CA / CL Position**, you'll see a more informative representation. It allows us to distinguish between individual drops.
- Each drop's behavior becomes clearer, aiding in analysis.

![Experiments](https://github.com/ag-gipp/Electronic-Laboratory-Notebook/blob/master/Readme_img/Drops.png)

## 7. Adding a New Experiment

Adding a new file to the lab book is straightforward. Simply copy the file into the existing folder structure. For example, let’s say we have a file saved at the following path:

      01_Data\01_Main_Exp\01_OCA_35_XL\20210201\Probe_BA_01\171700_osz_wasser_laengest.png

From this path, we can extract valuable information:

- The measurement was recorded on February 1st at 17:17:00.
- The sample used was labeled as BA_01 in the OCA experiment.

Remember that files older than 15 days or with incorrect file extensions will be ignored.

To add a completely new experiment:

- Go to the 01_data folder.
- Access the main experiments and then the Oca subfolder.
- Duplicate an existing experiment folder.
- Rename the copied folder with a date from the last 15 days.
- Finally, in your browser, click on Generate / Main to create the new entry.


# Creating a Custom Model

In this project, we'll guide you through the process of creating a custom model for your specific experiment. Follow the steps below to get started:

## 1. Uncomment Sections
Throughout the code, look for comments labeled **TODO add model**. Uncomment these sections to enable the following functionalities:

1. **Setting the location**:
   - In order to tell the programm where to search for new experiments got to `http://127.0.0.1:8000/admin/`
   - Sign in with the user: `admin` and password: `admin`
   - Create a new entry in `Exp path`

![Experiments](https://github.com/ag-gipp/Electronic-Laboratory-Notebook/blob/master/Readme_img/Add_DRP.png)


2. **Model Creation**:
   - Create a model for the main experiment (`Exp_Main/models`). This model will handle the core functionality of your experiment.
   - The model name should consist of 3 capital letters.
   - Additionally, create a model for the plot (`Lab_Dash/models`). The dashboard model is essential for manipulating and displaying the data.

3. **Reading Data from the 04_drop**:
   - The lab book will read in the data saved in the `04_drop` folder.
   - Specifically, you'll have added a **load data procedure** (`Lab_Misc/Load_Data`) that extracts data from an umpire file.

4. **Displaying Data**:
   - Develop the file responsible for displaying the experiment data (`Lab_Dash/dash_plot_DRP`).

5. **Database Considerations**:
   - If you've installed the lab book natively on your computer, you'll need to update the database.
   - Make the necessary migrations to the database and apply them. Refer to the Django documentation for detailed instructions.

6. **Running in Docker**:
   - If you're running the program in Docker, use the following command to build and start the containers:
     ```
     docker-compose up --build
     ```

7. **Adding a New Experiment**:
   - Finally, in your browser, click on **Generate / Main** to add the new entry to the database along with metadata from the folder.

That's it! You're now on your way to creating a custom model tailored to your experiment. Remember to adapt these steps based on your project's requirements and structure.


# Add a New Sample

To add a new sample, follow these steps:

1. Navigate to http://127.0.0.1:8000/admin/ and log in with the username: `admin` and password: `admin`.
2. Go to **Lab_Misc** and click on **samplebrushpnipaamsi**.
3. Add a proper name for your sample, consisting of two letters and two numbers separated by an underscore.
4. Click **Save**.
5. Now you can use this sample name in the folder structure and add a sample as described above.
6. Consider defining your own model for the sample, inheriting from `Sample_Blanks`.
7. For further details about models, visit the Django documentation.


# Navive installation

If you install the labbook natively on your computer, you will also have access to Jupyter. 
To open Jupyter, click on `Analysis`, and then select `Open Jupyter`.
If you have installed it natively, you can create an environment variable called ‘Experimental’ and set it to your data directory.
In case you want to use a customized Labbook version, create an environment variable named `DJANGO_SETTINGS_MODULE` to specify the relative path to your customized `manage.py` file.


# Contributing

Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change. Please make sure to update tests as appropriate.
