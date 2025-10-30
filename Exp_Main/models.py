from django.db import models
from datetime import datetime
from mptt.models import MPTTModel, TreeForeignKey, TreeManyToManyField
from Lab_Dash.models import OCA as OCA_dash
from Lab_Dash.models import RSD as RSD_dash
from Lab_Dash.models import SFG as SFG_dash
from Lab_Dash.models import SEL as SEL_dash
from Lab_Dash.models import GRP as GRP_dash
from Lab_Dash.models import LMP as LMP_dash
from Lab_Dash.models import GRV as GRV_dash
from Lab_Dash.models import DAF as DAF_dash
#from Lab_Dash.models import DRP as DRP_dash#TODO add Model
from Lab_Dash.models import Comparison as Comparison_dash
from Lab_Misc.models import SampleBase, OszScriptGen
from Lab_Misc.models import ProjectEntry as Project
from Exp_Sub.models import ExpBase as SubExp_base

'''class Idea(MPTTModel):
    Name = models.TextField(blank=True, null=True)
    Description = models.TextField(blank=True, null=True)
    parent = TreeForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='children')
    class MPTTMeta:
        order_insertion_by = ['Name']
    def __str__(self):
        return str(self.Name)'''

class Liquid(models.Model):
    Name = models.TextField()
    Born = models.DateTimeField(default=datetime.now(), null=True, blank=True)
    Death = models.DateTimeField(default=datetime.now(), null=True, blank=True)
    Description = models.TextField(blank=True, null=True)
    def __str__(self):
        return str(self.Name)

class ExpType(models.Model):
    Name = models.TextField(db_column='Name:', unique=True, blank=True, null=True)  # Field name made lowercase. Field renamed to remove unsuitable characters. Field renamed because it ended with '_'.
    Description = models.TextField(db_column='Description:', blank=True, null=True)  # Field name made lowercase. Field renamed to remove unsuitable characters. Field renamed because it ended with '_'.
    def __str__(self):
        return str(self.Name)

class Observation(models.Model):
    Name = models.TextField(db_column='Name:', unique=True, blank=True, null=True)  # Field name made lowercase. Field renamed to remove unsuitable characters. Field renamed because it ended with '_'.
    Description = models.TextField(db_column='Description:', blank=True, null=True)  # Field name made lowercase. Field renamed to remove unsuitable characters. Field renamed because it ended with '_'.
    def __str__(self):
        return str(self.Name)

class ObservationHierarchy(MPTTModel):
    Name = models.TextField(db_column='Name:', unique=True, blank=True, null=True)  # Field name made lowercase. Field renamed to remove unsuitable characters. Field renamed because it ended with '_'.
    Description = models.TextField(db_column='Description:', blank=True, null=True)  # Field name made lowercase. Field renamed to remove unsuitable characters. Field renamed because it ended with '_'.
    Observation = models.ManyToManyField(Observation, blank=True)
    parent = TreeForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='children')
    class MPTTMeta:
        order_insertion_by = ['Name']
    def __str__(self):
        return str(self.Name)

class FileEnding(models.Model):
    Name = models.TextField(unique=True, blank=True, null=True)
    Ending = models.TextField(unique=True)
    Comment = models.TextField(blank=True, null=True)
    def __str__(self):
        return self.Ending

class ExpPath(MPTTModel):
    Abbrev = models.CharField(max_length=3, unique=True)
    Name = models.TextField(unique=True)
    Path = models.TextField(unique=True)
    PathProcessedData = models.TextField(null=True, blank=True)
    File_ending = models.ManyToManyField(FileEnding, blank=True)
    parent = TreeForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='children')
    class MPTTMeta:
        order_insertion_by = ['-Name']
    def __str__(self):
        return str(self.Name)

class ExpBase(models.Model):
    """ExpBase Model to store the core of all experiments

    Parameters
    ----------
    models : [type]
        [description]

    Returns
    -------
    str
        Name of sample
    """
    Name = models.TextField(unique=True, null=True, blank=True)
    Sample_name = models.ForeignKey(SampleBase, on_delete=models.CASCADE)
    Date_time = models.DateTimeField(default=datetime(1900, 1, 1, 0, 0, 0), blank=True)
    Device = models.ForeignKey(ExpPath, on_delete=models.CASCADE)
    Comment = models.TextField(blank=True, null=True)
    Observation = models.ManyToManyField(Observation, blank=True)
    Project = models.ManyToManyField(Project, blank=True)
    Type = models.ManyToManyField(ExpType, blank=True)
    #Idea = TreeManyToManyField(Idea, blank=True)
    def __str__(self):
        return str(self.Name)
    def save(self, *args, **kwargs):#saves '' as none
         if not self.Name:
              self.Name = None
         super(ExpBase, self).save(*args, **kwargs)

class Group(MPTTModel):
    Name = models.TextField(db_column='Name:', unique=True, blank=True, null=True)  # Field name made lowercase. Field renamed to remove unsuitable characters. Field renamed because it ended with '_'.
    Sample_name = models.ForeignKey(SampleBase, on_delete=models.CASCADE, blank=True, null=True)
    Date_time = models.DateTimeField(default=datetime(1900, 1, 1, 0, 0, 0), blank=True)
    Device = models.ForeignKey(ExpPath, on_delete=models.CASCADE, blank=True, null=True)
    Comment = models.TextField(blank=True, null=True)
    Observation = models.ManyToManyField(Observation, blank=True)
    Type = models.ManyToManyField(ExpType, blank=True)
    Description = models.TextField(db_column='Description:', blank=True, null=True)  # Field name made lowercase. Field renamed to remove unsuitable characters. Field renamed because it ended with '_'.
    Dash = models.ForeignKey(GRP_dash, on_delete=models.CASCADE, blank=True, null=True)
    ExpBase = models.ManyToManyField(ExpBase, blank=True)
    parent = TreeForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='children')
    class MPTTMeta:
        order_insertion_by = ['Name']
    def __str__(self):
        return str(self.Name)

class GRP(ExpBase):
    """OCA Model to store all experiments done with the OCA

    Parameters
    ----------
    models : [type]
        [description]
    """
    Group = models.ForeignKey(Group, on_delete=models.CASCADE, blank=True, null=True)
    def __str__(self):
        return str(self.Name)

class OCA(ExpBase):
    """OCA Model to store all experiments done with the OCA

    Parameters
    ----------
    models : [type]
        [description]
    """
    Link = models.TextField(blank=True, null=True)
    Link_Data = models.TextField(blank=True, null=True)
    Link_PDF = models.TextField(blank=True, null=True)
    Link_Osz_join_LSP = models.TextField(blank=True, null=True)
    Dash = models.ForeignKey(OCA_dash, on_delete=models.CASCADE, blank=True, null=True)
    Sub_Exp = models.ManyToManyField(SubExp_base, blank=True)
    Liquid = models.ForeignKey(Liquid, on_delete=models.CASCADE, blank=True, null=True)
    Temp_Observation = models.TextField(blank=True, null=True)
    Temp_Hypothesis = models.TextField(blank=True, null=True)
    Temp_Mixing_ratio = models.TextField(blank=True, null=True)
    Temp_Atmosphere_relax = models.TextField(blank=True, null=True)
    Temp_Flowrate = models.TextField(blank=True, null=True)
    Temp_Volume = models.TextField(blank=True, null=True)
    Temp_Buzz_word = models.TextField(blank=True, null=True)
    Temp_Bath_time = models.TextField(blank=True, null=True)
    def __str__(self):
        return str(self.Name)

class LMP(ExpBase):
    """LMP Model to store all experiments done with the LMP

    Parameters
    ----------
    models : [type]
        [description]
    """
    Link = models.TextField(blank=True, null=True)
    Link_Data = models.TextField(blank=True, null=True)
    Link_PDF = models.TextField(blank=True, null=True)
    Link_Osz_join_LSP = models.TextField(blank=True, null=True)
    Chem_ETOH = models.FloatField(blank=True, null=True)
    Chem_H2O = models.FloatField(blank=True, null=True)
    Distance_s = models.FloatField(blank=True, null=True)#distance between grafting sites
    N_Monomers = models.FloatField(blank=True, null=True)#number of monomers
    w_pp = models.FloatField(blank=True, null=True)#interaction polymer polymer
    w_pw = models.FloatField(blank=True, null=True)#interaction polymer water
    w_pc = models.FloatField(blank=True, null=True)#interaction polymer cosolvent
    w_cc = models.FloatField(blank=True, null=True)#interaction cosolvent cosolvent
    w_cw = models.FloatField(blank=True, null=True)#interaction cosolvent water
    w_ww = models.FloatField(blank=True, null=True)#interaction water water
    N_ETOH = models.FloatField(blank=True, null=True)#number of ethanol
    N_H2O = models.FloatField(blank=True, null=True)#number of water
    Dash = models.ForeignKey(LMP_dash, on_delete=models.CASCADE, blank=True, null=True)
    Sub_Exp = models.ManyToManyField(SubExp_base, blank=True)
    def __str__(self):
        return str(self.Name)

class RSD(ExpBase):
    """OCA Model to store all experiments done with the OCA

    Parameters
    ----------
    models : [type]
        [description]
    """
    Link = models.TextField(blank=True, null=True)
    Link_Data = models.TextField(blank=True, null=True)
    Link_PDF = models.TextField(blank=True, null=True)
    Link_Osz_join_LSP = models.TextField(blank=True, null=True)
    Dash = models.ForeignKey(RSD_dash, on_delete=models.CASCADE, blank=True, null=True)
    Sub_Exp = models.ManyToManyField(SubExp_base, blank=True)
    Liquid = models.ForeignKey(Liquid, on_delete=models.CASCADE, blank=True, null=True)
    Script = models.ForeignKey(OszScriptGen, on_delete=models.CASCADE, blank=True, null=True)
    Temp_Observation = models.TextField(blank=True, null=True)
    Temp_Hypothesis = models.TextField(blank=True, null=True)
    Temp_Mixing_ratio = models.TextField(blank=True, null=True)
    Temp_Atmosphere_relax = models.TextField(blank=True, null=True)
    Temp_Flowrate = models.TextField(blank=True, null=True)
    Temp_Volume = models.TextField(blank=True, null=True)
    Temp_Buzz_word = models.TextField(blank=True, null=True)
    Temp_Bath_time = models.TextField(blank=True, null=True)
    def __str__(self):
        return str(self.Name)

class GRV(ExpBase):
    """OCA Model to store all experiments done with the OCA

    Parameters
    ----------
    models : [type]
        [description]
    """
    Liquid = models.ForeignKey(Liquid, on_delete=models.CASCADE, blank=True, null=True)
    Plate_speed_mm_s = models.FloatField(blank=True, null=True)
    Frame_rate = models.FloatField(blank=True, null=True)
    Dipping_angle = models.FloatField(blank=True, null=True)
    px_to_mm = models.FloatField(blank=True, null=True)
    Pix_Pos_0 = models.FloatField(blank=True, null=True)
    Link = models.TextField(blank=True, null=True)
    Link_Data = models.TextField(blank=True, null=True)
    Link_Data_processed = models.TextField(blank=True, null=True)
    Link_PDF = models.TextField(blank=True, null=True)
    Link_Osz_join_LSP = models.TextField(blank=True, null=True)
    Dash = models.ForeignKey(GRV_dash, on_delete=models.CASCADE, blank=True, null=True)
    Sub_Exp = models.ManyToManyField(SubExp_base, blank=True)
    Script = models.ForeignKey(OszScriptGen, on_delete=models.CASCADE, blank=True, null=True)
    Temp_Observation = models.TextField(blank=True, null=True)
    Temp_Hypothesis = models.TextField(blank=True, null=True)
    Temp_Mixing_ratio = models.TextField(blank=True, null=True)
    Temp_Atmosphere_relax = models.TextField(blank=True, null=True)
    Temp_Flowrate = models.TextField(blank=True, null=True)
    Temp_Volume = models.TextField(blank=True, null=True)
    Temp_Buzz_word = models.TextField(blank=True, null=True)
    Temp_Bath_time = models.TextField(blank=True, null=True)
    def __str__(self):
        return str(self.Name)

class LPT(ExpBase):
    """OCA Model to store all experiments done with the OCA

    Parameters
    ----------
    models : [type]
        [description]
    """
    Link = models.TextField(blank=True, null=True)
    Link_Data = models.TextField(blank=True, null=True)
    Link_PDF = models.TextField(blank=True, null=True)
    #Dash = models.ForeignKey(OCA_dash, on_delete=models.CASCADE, blank=True, null=True)
    Sub_Exp = models.ManyToManyField(SubExp_base, blank=True)
    Liquid = models.ForeignKey(Liquid, on_delete=models.CASCADE, blank=True, null=True)

    def __str__(self):
        return str(self.Name)

class SLD(ExpBase):
    """SLD Model to store all experiments done with the SLD

    Parameters
    ----------
    models : [type]
        [description]
    """
    Link = models.TextField(blank=True, null=True)
    Link_Data = models.TextField(blank=True, null=True)
    Link_PDF = models.TextField(blank=True, null=True)
    Temp_Observation = models.TextField(blank=True, null=True)
    Temp_Hypothesis = models.TextField(blank=True, null=True)
    Temp_Mixing_ratio = models.TextField(blank=True, null=True)
    Temp_Buzz_word = models.TextField(blank=True, null=True)
    Temp_Bath_time = models.TextField(blank=True, null=True)
    def __str__(self):
        return str(self.Name)

class CON(ExpBase):
    """OCA Model to store all experiments done with the OCA

    Parameters
    ----------
    models : [type]
        [description]
    """
    Link = models.TextField(blank=True, null=True)
    Link_Data = models.TextField(blank=True, null=True)
    Link_PDF = models.TextField(blank=True, null=True)
    Temp_Observation = models.TextField(blank=True, null=True)
    Temp_Hypothesis = models.TextField(blank=True, null=True)
    Temp_Mixing_ratio = models.TextField(blank=True, null=True)
    Temp_Buzz_word = models.TextField(blank=True, null=True)
    Temp_Bath_time = models.TextField(blank=True, null=True)
    def __str__(self):
        return str(self.Name)

class SEM(ExpBase):
    """OCA Model to store all experiments done with the OCA

    Parameters
    ----------
    models : [type]
        [description]
    """
    Link = models.TextField(blank=True, null=True)
    Link_Data = models.TextField(blank=True, null=True)
    Link_PDF = models.TextField(blank=True, null=True)
    Temp_Observation = models.TextField(blank=True, null=True)
    Temp_Hypothesis = models.TextField(blank=True, null=True)
    Temp_Buzz_word = models.TextField(blank=True, null=True)
    def __str__(self):
        return str(self.Name)

class RLD(ExpBase):
    """OCA Model to store all experiments done with the OCA

    Parameters
    ----------
    models : [type]
        [description]
    """
    Link = models.TextField(blank=True, null=True)
    Link_Data = models.TextField(blank=True, null=True)
    Link_PDF = models.TextField(blank=True, null=True)
    Temp_Observation = models.TextField(blank=True, null=True)
    Temp_Hypothesis = models.TextField(blank=True, null=True)
    Temp_Mixing_ratio = models.TextField(blank=True, null=True)
    Temp_Atmosphere_relax = models.TextField(blank=True, null=True)
    Temp_Flowrate = models.TextField(blank=True, null=True)
    Temp_Volume = models.TextField(blank=True, null=True)
    Temp_Buzz_word = models.TextField(blank=True, null=True)
    Temp_Bath_time = models.TextField(blank=True, null=True)
    t1 = models.TextField(blank=True, null=True)
    t2 = models.TextField(blank=True, null=True)
    t3 = models.TextField(blank=True, null=True)
    def __str__(self):
        return str(self.Name)

class NEL(ExpBase):
    """OCA Model to store all experiments done with the OCA

    Parameters
    ----------
    models : [type]
        [description]
    """
    Link_Video = models.TextField(blank=True, null=True)
    Link = models.TextField(blank=True, null=True)
    Link_PDF = models.TextField(blank=True, null=True)
    Temp_Observation = models.TextField(blank=True, null=True)
    Temp_Hypothesis = models.TextField(blank=True, null=True)
    Temp_Mixing_ratio = models.TextField(blank=True, null=True)
    Temp_Atmosphere_relax = models.TextField(blank=True, null=True)
    Temp_Flowrate = models.TextField(blank=True, null=True)
    Temp_Volume = models.TextField(blank=True, null=True)
    Temp_Buzz_word = models.TextField(blank=True, null=True)
    Temp_Bath_time = models.TextField(blank=True, null=True)
    def __str__(self):
        return str(self.Name)

class DIP(ExpBase):
    """OCA Model to store all experiments done with the OCA

    Parameters
    ----------
    models : [type]
        [description]
    """
    Link = models.TextField(blank=True, null=True)
    Link_Data = models.TextField(blank=True, null=True)
    Link_PDF = models.TextField(blank=True, null=True)
    Temp_Observation = models.TextField(blank=True, null=True)
    Temp_Hypothesis = models.TextField(blank=True, null=True)
    Temp_Mixing_ratio = models.TextField(blank=True, null=True)
    Temp_Atmosphere_relax = models.TextField(blank=True, null=True)
    Temp_Flowrate = models.TextField(blank=True, null=True)
    Temp_Volume = models.TextField(blank=True, null=True)
    Temp_Buzz_word = models.TextField(blank=True, null=True)
    Temp_Bath_time = models.TextField(blank=True, null=True)
    def __str__(self):
        return str(self.Name)

class KUR(ExpBase):
    """OCA Model to store all experiments done with the OCA

    Parameters
    ----------
    models : [type]
        [description]
    """
    Link = models.TextField(blank=True, null=True)
    Link_Data = models.TextField(blank=True, null=True)
    Link_PDF = models.TextField(blank=True, null=True)
    #Dash = models.ForeignKey(OCA_dash, on_delete=models.CASCADE, blank=True, null=True)
    Temp_Observation = models.TextField(blank=True, null=True)
    Temp_Hypothesis = models.TextField(blank=True, null=True)
    Temp_Mixing_ratio = models.TextField(blank=True, null=True)
    Temp_Atmosphere_relax = models.TextField(blank=True, null=True)
    Temp_Flowrate = models.TextField(blank=True, null=True)
    Temp_Volume = models.TextField(blank=True, null=True)
    Temp_Buzz_word = models.TextField(blank=True, null=True)
    Temp_Bath_time = models.TextField(blank=True, null=True)
    def __str__(self):
        return str(self.Name)

class LQB(ExpBase):
    """OCA Model to store all experiments done with the OCA

    Parameters
    ----------
    models : [type]
        [description]
    """
    Link = models.TextField(blank=True, null=True)
    Link_Data = models.TextField(blank=True, null=True)
    Link_PDF = models.TextField(blank=True, null=True)
    Temp_Observation = models.TextField(blank=True, null=True)
    Temp_Hypothesis = models.TextField(blank=True, null=True)
    Temp_Mixing_ratio = models.TextField(blank=True, null=True)
    Temp_Atmosphere_relax = models.TextField(blank=True, null=True)
    Temp_Flowrate = models.TextField(blank=True, null=True)
    Temp_Volume = models.TextField(blank=True, null=True)
    Temp_Buzz_word = models.TextField(blank=True, null=True)
    Temp_Bath_time = models.TextField(blank=True, null=True)
    def __str__(self):
        return str(self.Name)

class HEV(ExpBase):
    """OCA Model to store all experiments done with the OCA

    Parameters
    ----------
    models : [type]
        [description]
    """
    Link = models.TextField(blank=True, null=True)
    Link_Data = models.TextField(blank=True, null=True)
    Link_PDF = models.TextField(blank=True, null=True)
    Temp_Observation = models.TextField(blank=True, null=True)
    Temp_Hypothesis = models.TextField(blank=True, null=True)
    Temp_Mixing_ratio = models.TextField(blank=True, null=True)
    Temp_Atmosphere_relax = models.TextField(blank=True, null=True)
    Temp_Flowrate = models.TextField(blank=True, null=True)
    Temp_Volume = models.TextField(blank=True, null=True)
    Temp_Buzz_word = models.TextField(blank=True, null=True)
    Temp_Bath_time = models.TextField(blank=True, null=True)
    def __str__(self):
        return str(self.Name)

class NAF(ExpBase):
    """OCA Model to store all experiments done with the OCA

    Parameters
    ----------
    models : [type]
        [description]
    """
    Link_Video = models.TextField(blank=True, null=True)
    Link_Data = models.TextField(blank=True, null=True)
    Link = models.TextField(blank=True, null=True)
    Temp_Observation = models.TextField(blank=True, null=True)
    Temp_Hypothesis = models.TextField(blank=True, null=True)
    Temp_Mixing_ratio = models.TextField(blank=True, null=True)
    Temp_Atmosphere_relax = models.TextField(blank=True, null=True)
    Temp_Flowrate = models.TextField(blank=True, null=True)
    Temp_Volume = models.TextField(blank=True, null=True)
    Temp_Buzz_word = models.TextField(blank=True, null=True)
    Temp_Bath_time = models.TextField(blank=True, null=True)
    def __str__(self):
        return str(self.Name)

class SFG(ExpBase):
    """OCA Model to store all experiments done with the OCA

    Parameters
    ----------
    models : [type]
        [description]
    """
    Link_Video = models.TextField(blank=True, null=True)
    Link = models.TextField(blank=True, null=True)
    Link_PDF = models.TextField(blank=True, null=True)
    Dash = models.ForeignKey(SFG_dash, on_delete=models.CASCADE, blank=True, null=True)
    Temp_Observation = models.TextField(blank=True, null=True)
    Temp_Hypothesis = models.TextField(blank=True, null=True)
    Temp_Mixing_ratio = models.TextField(blank=True, null=True)
    Temp_Atmosphere_relax = models.TextField(blank=True, null=True)
    Temp_Flowrate = models.TextField(blank=True, null=True)
    Temp_Volume = models.TextField(blank=True, null=True)
    Temp_Buzz_word = models.TextField(blank=True, null=True)
    Temp_Bath_time = models.TextField(blank=True, null=True)
    XPos_mm = models.FloatField(blank=True, null=True)
    YPos_mm = models.FloatField(blank=True, null=True)
    PossiblePolarizations = [('1', 'PPP'), ('2', 'SSP')]
    Polarization = models.CharField(max_length=1, choices=PossiblePolarizations,blank=True, null=True)
    PossibleMeasurement_Modes = [('1', 'External Reflection'), ('2', 'Internal Reflection')]
    Measurement_Mode = models.CharField(max_length=1, choices=PossibleMeasurement_Modes,blank=True, null=True)
    def __str__(self):
        return str(self.Name)

class HED(ExpBase):
    """OCA Model to store all experiments done with the OCA

    Parameters
    ----------
    models : [type]
        [description]
    """
    Link_Video = models.TextField(blank=True, null=True)
    Link = models.TextField(blank=True, null=True)
    Link_PDF = models.TextField(blank=True, null=True)
    Liquid = models.ForeignKey(Liquid, on_delete=models.CASCADE, blank=True, null=True)
    Temp_Observation = models.TextField(blank=True, null=True)
    Temp_Hypothesis = models.TextField(blank=True, null=True)
    Temp_Mixing_ratio = models.TextField(blank=True, null=True)
    Temp_Atmosphere_relax = models.TextField(blank=True, null=True)
    Temp_Flowrate = models.TextField(blank=True, null=True)
    Temp_Volume = models.TextField(blank=True, null=True)
    Temp_Buzz_word = models.TextField(blank=True, null=True)
    Temp_Bath_time = models.TextField(blank=True, null=True)
    def __str__(self):
        return str(self.Name)

class SEL(ExpBase):
    """SEL Model to store all experiments done with the Spectroscopic ellipsometry

    Parameters
    ----------
    models : [type]
        [description]
    """
    Link_XLSX = models.TextField(blank=True, null=True)
    Link = models.TextField(blank=True, null=True)
    Link_PDF = models.TextField(blank=True, null=True)
    Dash = models.ForeignKey(SEL_dash, on_delete=models.CASCADE, blank=True, null=True)
    Sub_Exp = models.ManyToManyField(SubExp_base, blank=True)
    Temp_Observation = models.TextField(blank=True, null=True)
    Temp_Hypothesis = models.TextField(blank=True, null=True)
    Temp_Mixing_ratio = models.TextField(blank=True, null=True)
    Temp_Atmosphere_relax = models.TextField(blank=True, null=True)
    Temp_Flowrate = models.TextField(blank=True, null=True)
    Temp_Volume = models.TextField(blank=True, null=True)
    Temp_Buzz_word = models.TextField(blank=True, null=True)
    Temp_Bath_time = models.TextField(blank=True, null=True)
    def __str__(self):
        return str(self.Name)

class DAF(ExpBase):
    """DAF Model to store all experiments done with the DAFI

    Parameters
    ----------
    models : [type]
        [description]
    """
    Dash = models.ForeignKey(DAF_dash, on_delete=models.CASCADE, blank=True, null=True)
    Sub_Exp = models.ManyToManyField(SubExp_base, blank=True)
    Liquid = models.TextField(blank=True, null=True)
    Drop_Volume_muL = models.FloatField(blank=True, null=True)
    Rotations_per_min = models.FloatField(blank=True, null=True)
    Trajectory_Radius_mm = models.FloatField(blank=True, null=True)
    Velocity_mu_m_per_s = models.FloatField(blank=True, null=True)
    Height_Glass_Plate_mm = models.FloatField(blank=True, null=True)
    Capillary = models.IntegerField(blank=True, null=True)
    Link = models.TextField(blank=True, null=True)
    Link_Data = models.TextField(blank=True, null=True)
    Link_Data_2nd_Camera = models.TextField(blank=True, null=True)
    Link_Additional_Data_CAL = models.TextField(blank=True, null=True)
    Link_Additional_Data_CAR = models.TextField(blank=True, null=True)
    Link_Video = models.TextField(blank=True, null=True)
    Link_Video_2nd_Camera = models.TextField(blank=True, null=True)
    Link_Result = models.TextField(blank=True, null=True)
    def __str__(self):
        return str(self.Name)

'''class DRP(ExpBase):#TODO Add Model
    """DRP Model to store all experiments done with the DRP

    Parameters
    ----------
    models : [type]
        [description]
    """
    Link = models.TextField(blank=True, null=True)
    Dash = models.ForeignKey(DRP_dash, on_delete=models.CASCADE, blank=True, null=True)#adds connection to plot model
    Sub_Exp = models.ManyToManyField(SubExp_base, blank=True)#adds connection to sub exp
    def __str__(self):
        return str(self.Name)'''