import glob, os
import datetime
from .models import ExpPath, RSD
from Lab_Misc import General
from django.db.models import Q
import pandas as pd
import numpy as np
import cv2
from django.utils import timezone


def get_closest_to_dt(qs, dt):
    """
    get_closest_to_dt Gets closet entry to given datetime

    Gets closet entry to given datetime and retruns the closeset entry

    Parameters
    ----------
    qs : [type]
        query sting
    dt : datetime
        a chosen datetime

    Returns
    -------
    [type]
        The entry that is closest to the datetime
    """
    greater = qs.filter(Date_time__gte=dt).order_by("Date_time").first()
    less = qs.filter(Date_time__lte=dt).order_by("-Date_time").first()
    try:
        dt=dt.tz_convert(less.Date_time.tzinfo)
    except:
        dt=dt.tz_convert(greater.Date_time.tzinfo)
    if greater and less:
        return greater if abs(greater.Date_time - dt) < abs(less.Date_time - dt) else less
    else:
        return greater or less

def get_video_length(filepath):
    """
    Gets duration of given video file

    Parameters
    ----------
    filepath : string
        path to video file

    Returns
    -------
    float
        duration of video in seconds
    """
    video = cv2.VideoCapture(filepath)
    fps = video.get(cv2.CAP_PROP_FPS)
    frame_count = video.get(cv2.CAP_PROP_FRAME_COUNT)
    video.release()
    try:
        duration = frame_count/fps
    except:
        duration = 0
    return duration

def Sort_CON():
    con_path = ExpPath.objects.get(Abbrev = 'CON').Path
    os.chdir(os.path.join(General.get_BasePath(), con_path))

    for ending in ExpPath.objects.get(Abbrev = 'CON').File_ending.all().values_list('Ending', flat = True):
        for file in glob.glob('*.'+ending):
            record_time = os.path.getmtime(file)
            record_time = datetime.datetime.fromtimestamp(record_time) #convert to datetime format
            folder_name = str(record_time.strftime('%Y%m%d'))
            if not os.path.exists(folder_name):
                os.makedirs(folder_name)
            os.rename(file, os.path.join(folder_name,file))
    

    for date in glob.glob("*/"):
        os.chdir(date)
        old_record_time = datetime.datetime(2015, 1, 1, 12, 12, 12)
        for ending in ExpPath.objects.get(Abbrev = 'CON').File_ending.all().values_list('Ending', flat = True):
            for file in glob.glob('*.'+ending):
                record_time = os.path.getmtime(file)
                record_time = datetime.datetime.fromtimestamp(record_time) #convert to datetime format

                if record_time - old_record_time > datetime.timedelta(minutes=1):
                    folder_name = str(record_time.strftime('%H%M%S'))
                    if not os.path.exists(folder_name):
                        os.makedirs(folder_name)
                os.rename(file, os.path.join(folder_name,file))
                old_record_time = record_time
        os.chdir('..')
    os.chdir(cwd)


def Sort_RSD():
    con_path = ExpPath.objects.get(Abbrev = 'RSD').Path
    os.chdir(os.path.join(General.get_BasePath(), con_path))
    delay = 30
    times = [0,0]
    i = 1
    
    df = pd.DataFrame()
    files = []
    record_times = []
    for ending in ExpPath.objects.get(Abbrev = 'RSD').File_ending.all().values_list('Ending', flat = True):
        for file in glob.glob('*.'+ending):
            files.append(file)
            record_time = os.path.getmtime(file)
            record_time = datetime.datetime.fromtimestamp(record_time)
            record_time = record_time - datetime.timedelta(minutes=120) # in case of systematic shift
            record_times.append(record_time)
    df['files'] = files
    df['record_times'] = record_times
    df['record_times'] = df['record_times'].dt.tz_localize(timezone.get_current_timezone())
    df=df.sort_values(by ='record_times')
    df = df.reset_index(drop=True)

    while not len(df) == 0:
        record_time = df.iloc[0]['record_times']
        Exps_noVideo = RSD.objects.filter(Q(Link__isnull = True) | Q(Link__exact='')).order_by('Date_time')
        closest_entry = get_closest_to_dt(Exps_noVideo, record_time)
        delay = closest_entry.Script.delay
        link_df = closest_entry.Script.Link_gas_df
        pum_df = pd.read_pickle(os.path.join(General.get_BasePath(), link_df))
        times = pum_df[pum_df.columns[0][0]]['abs_time'].dropna()
        times = times[1:-2:2]
        times = np.asarray(times)
        date = str(record_time.strftime('%Y%m%d'))
        
        drop_times = []
        for time in times:
            drop_times.append(closest_entry.Date_time+datetime.timedelta(minutes = time+delay*0.5))
        
        to_drop = []
        for i in range(len(drop_times)-1):
            for j, rec_time in enumerate(df['record_times']):
                if (rec_time > drop_times[i]) & (rec_time < drop_times[i+1]):
                    time_str = str(record_time.strftime('%H%M%S'))
                    drop = 'Drop_' + str(i+1)
                    path = os.path.join(date, time_str, drop)
                    if not os.path.exists(path):
                        os.makedirs(path)
                    os.rename(df.iloc[j]['files'], os.path.join(path,df.iloc[j]['files']))
                    to_drop.append(j)
        for drop in to_drop[::-1]:
            df = df.drop([drop])
        
        if not len(df) == 0:
            df = df.reset_index(drop=True)
            df = df.drop([0])
    
    os.chdir(cwd)

def Sort_DAF():
    con_path = os.path.join(General.get_BasePath(), ExpPath.objects.get(Abbrev = 'DAF').Path)
    search_path = "Unsorted_Videos"
    os.chdir(os.path.join(con_path, search_path))

    for sample in glob.glob("*/"):
        os.chdir(sample)
        curr_path = os.getcwd()
        columns = ['files', 'old_paths', 'record_times', 'vid_lengths', 'endings']
        df = pd.DataFrame([["default", "default", datetime.datetime(2015, 1, 1, 12, 12, 12), 0, "default"]], columns=columns)
        exp_times = []

        for ending in ExpPath.objects.get(Abbrev = 'DAF').File_ending.all().values_list('Ending', flat = True): # list all files and times
            for file in glob.glob('*.'+ending):
                old_path = os.path.join(curr_path, file)
                record_time = os.path.getmtime(file)
                record_time = datetime.datetime.fromtimestamp(record_time) # convert to datetime format
                vid_length = get_video_length(old_path)
                newrow = pd.DataFrame([[file, old_path, record_time, vid_length, ending]], columns=columns)
                df = pd.concat([df, newrow], ignore_index=True)

        df['record_times'] = df['record_times'].dt.tz_localize(timezone.get_current_timezone())
        df=df.sort_values(by ='record_times')
        df = df.reset_index(drop=True)

        for i in range(1, len(df['files'])):
            if (df['record_times'][i] - df['record_times'][i-1]) > (datetime.timedelta(seconds=df['vid_lengths'][i-1]) + datetime.timedelta(seconds=10)): # more than 10 s between videos -> different measurements
                vid_no = 1
                exp_times.append(record_time)
                record_timestamp = str(df['record_times'][i].strftime('%H%M%S'))
                filename = df['files'][i]
                ending = df['endings'][i]
                date = str(df['record_times'][i].strftime('%Y%m%d'))
                date_path = os.path.join(con_path, date)
                if not os.path.exists(date_path):
                    os.makedirs(date_path)
                sample_path = os.path.join(date_path, sample)
                if not os.path.exists(sample_path):
                    os.makedirs(sample_path)
            else: # videos belong to same measurement
                vid_no += 1
            new_file = record_timestamp + '_' + filename.replace('.'+ending, '_'+str(vid_no)+'.'+df['endings'][i-vid_no+1])
            new_path = os.path.join(sample_path, new_file)
            os.rename(df['old_paths'][i], new_path)

        try: # sort videos of 2nd camera (in extra folder)
            os.chdir('2nd_Camera')
            curr_path_2nd = os.getcwd()
            exp_times = np.asarray(exp_times)
            df = pd.DataFrame([["default", "default", datetime.datetime(2015, 1, 1, 12, 12, 12), 0, "default"]], columns=columns)

            for ending in ExpPath.objects.get(Abbrev = 'DAF').File_ending.all().values_list('Ending', flat = True): # list all files and times
                for file in glob.glob('*.'+ending):
                    old_path = os.path.join(curr_path_2nd, file)
                    record_time = os.path.getmtime(file)
                    record_time = datetime.datetime.fromtimestamp(record_time)
                    #record_time = record_time + datetime.timedelta(hours=1) # if internal time of second camera differs from that of first camera
                    vid_length = get_video_length(old_path)
                    newrow = pd.DataFrame([[file, old_path, record_time, vid_length, ending]], columns=columns)
                    df = pd.concat([df, newrow], ignore_index=True)

            df['record_times'] = df['record_times'].dt.tz_localize(timezone.get_current_timezone())
            df=df.sort_values(by ='record_times')
            df = df.reset_index(drop=True)

            for i in range(1, len(df['files'])):
                if (df['record_times'][i] - df['record_times'][i-1]) > (datetime.timedelta(seconds=df['vid_lengths'][i-1]) + datetime.timedelta(seconds=10)): # more than 10 s between videos -> different measurements
                    vid_no = 1
                    idx = (np.abs(exp_times - record_time)).argmin()
                    record_timestamp = str(exp_times[idx].strftime('%H%M%S'))
                    filename = df['files'][i]
                    ending = df['endings'][i]
                    date = str(record_time.strftime('%Y%m%d'))
                    date_path = os.path.join(con_path, date)
                    sample_path = os.path.join(date_path, sample)
                else: # videos belong to same measurement
                    vid_no += 1
                new_file = record_timestamp + '_' + filename.replace('.'+ending, '_P_'+str(vid_no)+'.'+df['endings'][i-vid_no+1])
                new_path = os.path.join(sample_path, new_file)
                os.rename(df['old_paths'][i], new_path)

            os.chdir('..')
            if len(os.listdir(curr_path_2nd)) == 0: # delete directory of 2nd camera if all files have been moved to parent directory
                os.rmdir(curr_path_2nd)
            else:
                print(curr_path_2nd, 'cannot be deleted, because there are files left in the directory.')
        except:
            pass
        os.chdir(os.path.join(con_path, search_path))
        if len(os.listdir(curr_path)) == 0: # delete directory of sample if all files have been moved to parent directory
            os.rmdir(curr_path)
        else:
            print(curr_path, 'cannot be deleted, because there are files left in the directory.')
    os.chdir(cwd)

cwd = os.getcwd()
'''
is_not_first = False
for file in glob.glob("*.mov"):
    record_time = os.path.getmtime(file)
    record_time = datetime.datetime.fromtimestamp(record_time) #convert to datetime format

    if is_not_first:
        print(record_time - old_record_time)
    is_not_first = True
    old_record_time = record_time


os.chdir(os.path.join('../01_Messdaten/', date))


if not os.path.exists(date):
    os.makedirs(date)

for probe in glob.glob("*/"):
    os.chdir(probe)

for file in glob.glob("*.txt"):
        j +=1
'''