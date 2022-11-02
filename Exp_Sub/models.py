from django.db import models
from datetime import datetime
from mptt.models import MPTTModel, TreeForeignKey, TreeManyToManyField
# Create your models here.
class Liquid(models.Model):
    Name = models.TextField()
    Born = models.DateTimeField(default=datetime.now(), null=True, blank=True)
    Death = models.DateTimeField(default=datetime.now(), null=True, blank=True)
    Description = models.TextField(blank=True, null=True)
    def __str__(self):
        return str(self.Name)

class FileEnding(models.Model):
    Name = models.TextField(unique=True, blank=True, null=True)
    Ending = models.TextField(unique=True)
    Comment = models.TextField(blank=True, null=True)
    def __str__(self):
        return self.Ending

class Gas(models.Model):
    Name = models.TextField()
    Born = models.DateTimeField(default=datetime.now(), null=True, blank=True)
    Death = models.DateTimeField(default=datetime.now(), null=True, blank=True)
    Description = models.TextField(blank=True, null=True)
    def __str__(self):
        return str(self.Name)

class ExpPath(MPTTModel):
    Abbrev = models.CharField(max_length=3, unique=True)
    Name = models.TextField(unique=True)
    Path = models.TextField(unique=True)
    File_ending = models.ManyToManyField(FileEnding, blank=True)
    parent = TreeForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='children')
    class MPTTMeta:
        order_insertion_by = ['Name']
    def __str__(self):
        return str(self.Name)


class ExpBase(models.Model):
    """ExpBase Model to store the core of all sub experiments

    Parameters
    ----------
    models : [type]
        [description]

    Returns
    -------
    str
        Name of sample
    """
    Name = models.TextField(db_column='Name:', unique=True, blank=True, null=True)
    Date_time = models.DateTimeField(default=datetime(1900, 1, 1, 0, 0, 0), blank=True)
    Device = models.ForeignKey(ExpPath, on_delete=models.CASCADE)
    Comment = models.TextField(blank=True, null=True)

    def __str__(self):
        return str(self.Name)

class LSP(ExpBase):
    """LSP Model to store all experiments done with the LSP

    Parameters
    ----------
    models : [type]
        [description]
    """
    Liquid = models.ForeignKey(Liquid, on_delete=models.CASCADE, blank=True, null=True)
    Link = models.TextField(blank=True, null=True)
    def __str__(self):
        return str(self.Name)

class MFL(ExpBase):
    Gas = models.ManyToManyField(Gas)
    Link = models.TextField(blank=True, null=True)
    def __str__(self):
        return str(self.Name)

class MFR(ExpBase):
    Gas = models.ManyToManyField(Gas)
    Link = models.TextField(blank=True, null=True)
    def __str__(self):
        return str(self.Name)

class HME(ExpBase):
    """LSP Model to store all experiments done with the LSP

    Parameters
    ----------
    models : [type]
        [description]
    """
    Link = models.TextField(blank=True, null=True)
    PossibleEnvironments = [('1', 'Cell'), ('2', 'Room')]
    Environments = models.CharField(max_length=1, choices=PossibleEnvironments, default='1')
    def __str__(self):
        return str(self.Name)

class HIA(ExpBase):
    """LSP Model to store all experiments done with the LSP

    Parameters
    ----------
    models : [type]
        [description]
    """
    Link = models.TextField(blank=True, null=True)
    PossibleEnvironments = [('1', 'Cell'), ('2', 'Room')]
    Environments = models.CharField(max_length=1, choices=PossibleEnvironments, default='1')
    def __str__(self):
        return str(self.Name)

class TCM(ExpBase):
    """LSP Model to store all experiments done with the LSP

    Parameters
    ----------
    models : [type]
        [description]
    """
    Link = models.TextField(blank=True, null=True)
    def __str__(self):
        return str(self.Name)

class CAP(ExpBase):
    """CAP Model to store all experiments in order to determine
    the spring constant of the capillary used in DAFI experiments

    Parameters
    ----------
    models : [type]
        [description]
    """
    Capillary = models.IntegerField(blank=True, null=True)
    Link = models.TextField(blank=True, null=True)
    Link_Data = models.TextField(blank=True, null=True)
    FPS = models.FloatField(blank=True, null=True)
    Total_Length_mm = models.FloatField(blank=True, null=True, default=50)
    Width_mm = models.FloatField(blank=True, null=True, default=0.4)
    Height_mm = models.FloatField(blank=True, null=True, default=0.04)
    Wall_Thickness_mm = models.FloatField(blank=True, null=True, default=0.028)
    Mass_g = models.FloatField(blank=True, null=True)
    Effective_Length_mm = models.FloatField(blank=True, null=True)
    Glass_Plate = models.BooleanField(blank=True, null=True)
    Fixture_Mass_without_Glass_Plate_g = models.FloatField(blank=True, null=True)
    Fixture_Mass_with_Glass_Plate_g = models.FloatField(blank=True, null=True)
    Eigenfrequency_Hz = models.FloatField(blank=True, null=True)
    Spring_Constant_N_per_m = models.FloatField(blank=True, null=True)
    Delta_Spring_Constant_N_per_m = models.FloatField(blank=True, null=True)
    def __str__(self):
        return str(self.Name)
