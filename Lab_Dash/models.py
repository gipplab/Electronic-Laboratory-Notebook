from django.db import models
from datetime import datetime

# Create your models here.
class OCA(models.Model):
    """OCA Saves all dash properties of the OCA measurements

    Parameters
    ----------
    models : [type]
        [description]
    """    
    Name = models.TextField(unique=True, blank=True, null=True)
    CA_high_degree = models.FloatField(blank=True, null=True)
    CA_low_degree = models.FloatField(blank=True, null=True)
    BD_high_mm = models.FloatField(blank=True, null=True)
    BD_low_mm = models.FloatField(blank=True, null=True)
    Time_high_sec = models.FloatField(blank=True, null=True)
    Time_low_sec = models.FloatField(blank=True, null=True)
    Time_diff_pump = models.FloatField(blank=True, null=True)
    Cycle_drop_1_sec = models.FloatField(blank=True, null=True)
    Cycle_drop_2_sec = models.FloatField(blank=True, null=True)
    Cycle_drop_3_sec = models.FloatField(blank=True, null=True)
    Cycle_drop_4_sec = models.FloatField(blank=True, null=True)
    Cycle_drop_5_sec = models.FloatField(blank=True, null=True)
    Cycle_drop_6_sec = models.FloatField(blank=True, null=True)
    def __str__(self):
        return str(self.Name)
    def save(self, *args, **kwargs):#saves '' as none
        if not self.Name:
            self.Name = None
        super(OCA, self).save(*args, **kwargs)

class LMP(models.Model):
    """LMP Saves all dash properties of the LMP measurements

    Parameters
    ----------
    models : [type]
        [description]
    """    
    Name = models.TextField(unique=True, blank=True, null=True)
    CA_high_degree = models.FloatField(blank=True, null=True)
    CA_low_degree = models.FloatField(blank=True, null=True)
    BD_high_mm = models.FloatField(blank=True, null=True)
    BD_low_mm = models.FloatField(blank=True, null=True)
    Time_high_sec = models.FloatField(blank=True, null=True)
    Time_low_sec = models.FloatField(blank=True, null=True)
    Time_diff_pump = models.FloatField(blank=True, null=True)
    def __str__(self):
        return str(self.Name)
    def save(self, *args, **kwargs):#saves '' as none
        if not self.Name:
            self.Name = None
        super(LMP, self).save(*args, **kwargs)

class RSD(models.Model):
    """RSD Saves all dash properties of the RSD measurements

    Parameters
    ----------
    models : [type]
        [description]
    """    
    Name = models.TextField(unique=True, blank=True, null=True)
    CA_high_degree = models.FloatField(blank=True, null=True)
    CA_low_degree = models.FloatField(blank=True, null=True)
    BD_high_mm = models.FloatField(blank=True, null=True)
    BD_low_mm = models.FloatField(blank=True, null=True)
    Time_high_sec = models.FloatField(blank=True, null=True)
    Time_low_sec = models.FloatField(blank=True, null=True)
    Time_diff_pump = models.FloatField(blank=True, null=True)
    def __str__(self):
        return str(self.Name)
    def save(self, *args, **kwargs):#saves '' as none
        if not self.Name:
            self.Name = None
        super(RSD, self).save(*args, **kwargs)

class SEL(models.Model):
    """SEL Saves all dash properties of the SEL measurements

    Parameters
    ----------
    models : [type]
        [description]
    """    
    Name = models.TextField(unique=True, blank=True, null=True)
    Start_datetime_elli = models.DateTimeField(default=datetime.now(), null=True, blank=True)
    def __str__(self):
        return str(self.Name)
    def save(self, *args, **kwargs):#saves '' as none
         if not self.Name:
              self.Name = None
         super(SEL, self).save(*args, **kwargs)

class ComparisonEntry(models.Model):
    """SEL Saves all dash properties of the SEL measurements

    Parameters
    ----------
    models : [type]
        [description]
    """    
    Name = models.TextField(blank=True, null=True)
    Label = models.TextField(blank=True, null=True)
    ExpBaseID = models.IntegerField(blank=True, null=True)#Foreign key not possible because of circular import
    X_high = models.FloatField(blank=True, null=True)
    X_low = models.FloatField(blank=True, null=True)
    Y_high = models.FloatField(blank=True, null=True)
    Y_low = models.FloatField(blank=True, null=True)
    X_shift = models.FloatField(blank=True, null=True)
    Y_shift = models.FloatField(blank=True, null=True)
    def __str__(self):
        return str(self.Name)
    def save(self, *args, **kwargs):#saves '' as none
         if not self.Name:
              self.Name = None
         super(ComparisonEntry, self).save(*args, **kwargs)

class Comparison(models.Model):
    """SEL Saves all dash properties of the SEL measurements

    Parameters
    ----------
    models : [type]
        [description]
    """    
    Name = models.TextField(blank=True, null=True)
    Title = models.TextField(blank=True, null=True)
    Entry = models.ManyToManyField(ComparisonEntry, blank=True)
    X_shift = models.FloatField(blank=True, null=True)
    Y_shift = models.FloatField(blank=True, null=True)
    X_high = models.FloatField(blank=True, null=True)
    X_low = models.FloatField(blank=True, null=True)
    Y_high = models.FloatField(blank=True, null=True)
    Y_low = models.FloatField(blank=True, null=True)
    def __str__(self):
        return str(self.Name)
    def save(self, *args, **kwargs):#saves '' as none
         if not self.Name:
              self.Name = None
         super(Comparison, self).save(*args, **kwargs)

class OszAnalysisEntry(models.Model):
    """SEL Saves all dash properties of the SEL measurements

    Parameters
    ----------
    models : [type]
        [description]
    """    
    Name = models.TextField(blank=True, null=True)
    Label = models.TextField(blank=True, null=True)
    OszAnalysisID = models.IntegerField(blank=True, null=True)#Foreign key not possible because of circular import
    X_high = models.FloatField(blank=True, null=True)
    X_low = models.FloatField(blank=True, null=True)
    Y_high = models.FloatField(blank=True, null=True)
    Y_low = models.FloatField(blank=True, null=True)
    X_shift = models.FloatField(blank=True, null=True)
    Y_shift = models.FloatField(blank=True, null=True)
    def __str__(self):
        return str(self.Name)
    def save(self, *args, **kwargs):#saves '' as none
         if not self.Name:
              self.Name = None
         super(OszAnalysisEntry, self).save(*args, **kwargs)
class OszAnalysis(models.Model):
    """SEL Saves all dash properties of the SEL measurements

    Parameters
    ----------
    models : [type]
        [description]
    """    
    Name = models.TextField(blank=True, null=True)
    Title = models.TextField(blank=True, null=True)
    Entry = models.ManyToManyField(OszAnalysisEntry, blank=True)
    X_shift = models.FloatField(blank=True, null=True)
    Y_shift = models.FloatField(blank=True, null=True)
    X_high = models.FloatField(blank=True, null=True)
    X_low = models.FloatField(blank=True, null=True)
    Y_high = models.FloatField(blank=True, null=True)
    Y_low = models.FloatField(blank=True, null=True)
    def __str__(self):
        return str(self.Name)
    def save(self, *args, **kwargs):#saves '' as none
         if not self.Name:
              self.Name = None
         super(OszAnalysis, self).save(*args, **kwargs)

class SFG(models.Model):
    """SEL Saves all dash properties of the SEL measurements

    Parameters
    ----------
    models : [type]
        [description]
    """    
    Name = models.TextField(unique=True, blank=True, null=True)
    def __str__(self):
        return str(self.Name)
    def save(self, *args, **kwargs):#saves '' as none
         if not self.Name:
              self.Name = None
         super(SFG, self).save(*args, **kwargs)

class GRP(models.Model):
    Name = models.TextField(unique=True, blank=True, null=True)
    PossibleTyps = [('SFG_kin_3D', 'Sum frequency generation kinetic'), ('SFG_kin_drive', 'Sum frequency generation kinetic while changing the Position'),
                    ('SFG_abrastern', 'Sum frequency generation at different locations'), ('SFG_cycle', 'Sum frequency generation cycle drops')]
    Typ = models.TextField(choices=PossibleTyps, blank=True, null=True)
    def __str__(self):
        return str(self.Name)

class SFG_cycle(models.Model):
    Name = models.TextField(unique=True)
    Graph_distance = models.FloatField(blank=True, null=True)
    Signal_high = models.FloatField(blank=True, null=True)
    Signal_low = models.FloatField(blank=True, null=True)
    Wavenumber_high = models.FloatField(blank=True, null=True)
    Wavenumber_low = models.FloatField(blank=True, null=True)
    Group = models.ForeignKey(GRP, on_delete=models.CASCADE, blank=True, null=True)
    def __str__(self):
        return str(self.Name)

class SFG_abrastern(models.Model):
    Name = models.TextField(unique=True)
    Graph_distance = models.FloatField(blank=True, null=True)
    Signal_high = models.FloatField(blank=True, null=True)
    Signal_low = models.FloatField(blank=True, null=True)
    Wavenumber_high = models.FloatField(blank=True, null=True)
    Wavenumber_low = models.FloatField(blank=True, null=True)
    Group = models.ForeignKey(GRP, on_delete=models.CASCADE, blank=True, null=True)
    def __str__(self):
        return str(self.Name)

class SFG_kin_3D(models.Model):
    Name = models.TextField(unique=True)
    Time_high_sec = models.FloatField(blank=True, null=True)
    Time_low_sec = models.FloatField(blank=True, null=True)
    Signal_high = models.FloatField(blank=True, null=True)
    Signal_low = models.FloatField(blank=True, null=True)
    Wavenumber_high = models.FloatField(blank=True, null=True)
    Wavenumber_low = models.FloatField(blank=True, null=True)
    Group = models.ForeignKey(GRP, on_delete=models.CASCADE, blank=True, null=True)
    def __str__(self):
        return str(self.Name)

class SFG_kin_drive(models.Model):
    Name = models.TextField(unique=True)
    Time_high_sec = models.FloatField(blank=True, null=True)
    Time_low_sec = models.FloatField(blank=True, null=True)
    Signal_high = models.FloatField(blank=True, null=True)
    Signal_low = models.FloatField(blank=True, null=True)
    Wavenumber_high = models.FloatField(blank=True, null=True)
    Wavenumber_low = models.FloatField(blank=True, null=True)
    Group = models.ForeignKey(GRP, on_delete=models.CASCADE, blank=True, null=True)
    def __str__(self):
        return str(self.Name)

class KUR(models.Model):
    Name = models.TextField(unique=True)
    CA_high_degree = models.FloatField(blank=True, null=True)
    CA_low_degree = models.FloatField(blank=True, null=True)
    BD_high_mm = models.FloatField(blank=True, null=True)
    BD_low_mm = models.FloatField(blank=True, null=True)
    Time_high_sec = models.FloatField(blank=True, null=True)
    Time_low_sec = models.FloatField(blank=True, null=True)
    def __str__(self):
        return str(self.Name)