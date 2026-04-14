import os
import time
import psutil
import torch
import math
import pickle
import traceback
import numpy as np
import pandas as pd
from datetime import datetime
from cellpose import models
from skimage import exposure
from skimage.measure import regionprops
from scipy.ndimage import center_of_mass
from scipy.optimize import linear_sum_assignment
from scipy.spatial.distance import cdist

from Lab_Misc.Load_Data import Load_MFP_Video
from Exp_Main.models import MFP
from Analysis.models import MFPAnalysis

# =========================================================
# 1. DER TÜRSTEHER (Ressourcen-Check)
# =========================================================
def wait_for_free_resources(required_ram_gb=10, required_vram_gb=5, max_cpu_percent=80):
    print("🔍 Prüfe Server-Auslastung vor dem Start...")
    while True:
        cpu_usage = psutil.cpu_percent(interval=1)
        free_ram_gb = psutil.virtual_memory().available / (1024 ** 3)
        
        free_vram_gb = 100 # Fallback
        if torch.cuda.is_available():
            free_vram, _ = torch.cuda.mem_get_info()
            free_vram_gb = free_vram / (1024 ** 3)
            
        if cpu_usage < max_cpu_percent and free_ram_gb > required_ram_gb and free_vram_gb > required_vram_gb:
            print(f"✅ Ressourcen frei! (CPU: {cpu_usage}%, RAM: {free_ram_gb:.1f}GB, VRAM: {free_vram_gb:.1f}GB)")
            return True 
        else:
            print(f"⚠️ Server ausgelastet. Warte 60 Sekunden...")
            time.sleep(60)

# =========================================================
# 2. DIE KI KLASSE
# =========================================================
class ServerCellposeAnalysis:
    def __init__(self, entry_id, diameter=99):
        self.diameter = diameter
        # Begrenze die GPU auf 15% pro Worker, falls CUDA da ist!
        if torch.cuda.is_available():
            torch.cuda.set_per_process_memory_fraction(0.15)
        self.use_gpu = torch.cuda.is_available() 
        
        model_path = '/Users/simon/01_Experimental/Electronic-Laboratory-Notebook/Private/Cellpose_Trainingsdaten/Super_Training_Mix/models/cellpose_1775998269.051098'
        self.model = models.CellposeModel(gpu=self.use_gpu, pretrained_model=model_path)

    def analyze_frame(self, video_data, frame_idx):
        # [Dein exakter Code aus 'analyze_whole_frame' kommt hier rein: Bilder laden, normalisieren, model.eval, regionprops, etc.]
        # ... (Ich kürze das hier der Übersichtlichkeit halber ab, nutze deinen bekannten Code)
        pass 

# =========================================================
# 3. DER EIGENTLICHE JOB (Für exakt 1 Video)
# =========================================================
def run_single_analysis(entry_id):
    """Dieser Job wird vom Cluster ausgeführt"""
    
    # 1. TÜRSTEHER FRAGEN
    wait_for_free_resources(required_ram_gb=10, required_vram_gb=4, max_cpu_percent=85)
    
    analysis_obj = MFPAnalysis.objects.get(Entry_id=entry_id)
    pkl_path = f"/tmp/Cellpose_{entry_id}.pkl"
    
    try:
        video_data = Load_MFP_Video(entry_id)
        analyzer = ServerCellposeAnalysis(entry_id, diameter=analysis_obj.Particle_Diameter)
        num_frames = len(video_data['brightfield'])
        
        all_results = []
        # Frame-Loop ohne Timeout-Hack, weil Django-Q2 das Timeout regelt!
        for frame_idx in range(num_frames):
            frame_results = analyzer.analyze_frame(video_data, frame_idx)
            all_results.extend(frame_results)
            
        # Tracking & Speichern (Dein bekannter Tracking-Code)
        # ...
        
        # Datenbank Update
        analysis_obj.status = MFPAnalysis.Status.COMPLETED
        analysis_obj.Result_Path = pkl_path
        analysis_obj.save()
        return f"Erfolg: ID {entry_id}"
        
    except Exception as e:
        analysis_obj.status = MFPAnalysis.Status.FAILED
        analysis_obj.error_message = str(e)
        analysis_obj.save()
        raise e # Fehler an den Cluster weitergeben, damit er im Admin-Panel auftaucht!