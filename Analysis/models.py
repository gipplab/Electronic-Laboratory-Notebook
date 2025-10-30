from django.db import models
from Lab_Dash.models import Comparison as Comparison_dash
from Lab_Dash.models import GrvAnalysis as GrvAnalysis_dash
from Lab_Dash.models import OszAnalysis as OszAnalysis_dash
from Lab_Dash.models import DafAnalysis as DafAnalysis_dash
from Exp_Main.models import ExpBase, DAF

# Create your models here.
class Comparison(models.Model):
    """SEL Saves all dash properties of the SEL measurements

    Parameters
    ----------
    models : [type]
        [description]
    """    
    Name = models.TextField(unique=True, blank=True, null=True)
    ExpBase = models.ManyToManyField(ExpBase, blank=True)
    Dash = models.ForeignKey(Comparison_dash, null=True, blank=True, on_delete=models.CASCADE)
    def __str__(self):
        return str(self.Name)
    def save(self, *args, **kwargs):#saves '' as none
         if not self.Name:
              self.Name = None
         super(Comparison, self).save(*args, **kwargs)

class PointsShift(models.Model):
    Pos_ch = [('upper_on_hill', 'upper_on_hill'), ('upper_on_plate', 'upper_on_plate'),
              ('white_upper_on_hill', 'white_upper_on_hill'), ('white_upper_on_plate', 'white_upper_on_plate'), ('lower_in_groove', 'lower_in_groove'), 
              ('upper_in_groove', 'upper_in_groove'), ('on_hill_edge', 'on_hill_edge'), 
              ('white_lower_in_groove', 'white_lower_in_groove'), ('white_upper_in_groove', 'white_upper_in_groove')]
    Type_pos = models.TextField(choices=Pos_ch, blank=True, null=True)
    Position = models.FloatField(blank=True, null=True)

class SteadyShift(models.Model):
    Frame = models.IntegerField(blank=True, null=True)
    NrAvrgFrame = models.IntegerField(default=3, blank=True, null=True)
    state_ch = [('steady', 'steady'), 
           ('static', 'static')]
    Type_state = models.TextField(choices=state_ch, blank=True, null=True)
    PointsShift = models.ManyToManyField(PointsShift, blank=True)

class GrvAnalysis(models.Model):
    Name = models.TextField(null=True, blank=True)
    SteadyShift = models.ManyToManyField(SteadyShift, blank=True)
    Exp = models.ForeignKey(ExpBase, on_delete=models.CASCADE, blank=True, null=True)
    def __str__(self):
        return str(self.Name)

class GrvAnalysisJoin(models.Model):
    """SEL Saves all dash properties of the SEL measurements

    Parameters
    ----------
    models : [type]
        [description]
    """    
    Name = models.TextField(unique=True, blank=True, null=True)
    GrvAnalysis = models.ManyToManyField(GrvAnalysis, blank=True)
    Dash = models.ForeignKey(GrvAnalysis_dash, blank=True, on_delete=models.CASCADE)
    def __str__(self):
        return str(self.Name)
    def save(self, *args, **kwargs):#saves '' as none
         if not self.Name:
              self.Name = None
         super(GrvAnalysisJoin, self).save(*args, **kwargs)


class OszBaseParam(models.Model):
    Drop_Nr = models.IntegerField(blank=True, null=True)
    LoR = [('Left', 'Left'), ('Right', 'Right')]
    LoR_CL = models.TextField(choices=LoR, blank=True, null=True)
    Max_CL = models.FloatField(blank=True, null=True)
    Max_CA = models.FloatField(blank=True, null=True)
    Min_CA = models.FloatField(blank=True, null=True)
    Min_AdvCA = models.FloatField(blank=True, null=True)

class OszFitRes(models.Model):
    Drop_Nr = models.IntegerField(blank=True, null=True)
    LoR = [('Left', 'Left'), ('Right', 'Right')]
    LoR_CL = models.TextField(choices=LoR, blank=True, null=True)
    ErroVal_pos = [('Value', 'Value'), ('Error', 'Error')]
    ErroVal = models.TextField(choices=ErroVal_pos, blank=True, null=True)
    x_pos = models.FloatField(blank=True, null=True)
    y_pos = models.FloatField(blank=True, null=True)
    Step_width = models.FloatField(blank=True, null=True)
    Step_hight = models.FloatField(blank=True, null=True)

class OszDerivedRes(models.Model):
    Drop_Nr = models.IntegerField(blank=True, null=True)
    LoR = [('Left', 'Left'), ('Right', 'Right')]
    LoR_CL = models.TextField(choices=LoR, blank=True, null=True)
    Hit_prec = models.FloatField(blank=True, null=True)
    Fit_score = models.FloatField(blank=True, null=True)

class OszAnalysis(models.Model):
    Name = models.TextField(unique=True)
    OszBaseParam = models.ManyToManyField(OszBaseParam, blank=True)
    OszFitRes = models.ManyToManyField(OszFitRes, blank=True)
    OszDerivedRes = models.ManyToManyField(OszDerivedRes, blank=True)
    Drop_center = models.FloatField(blank=True, null=True)
    Hit_prec = models.FloatField(blank=True, null=True)
    Exp = models.ForeignKey(ExpBase, on_delete=models.CASCADE, blank=True, null=True)
    def __str__(self):
        return str(self.Name)

class LMPCosolventAnalysis(models.Model):
    Name = models.TextField(unique=True)
    Anz_H2O = models.FloatField(blank=True, null=True)
    Anz_EtOH = models.FloatField(blank=True, null=True)
    Height = models.FloatField(blank=True, null=True)
    Height_Err = models.FloatField(blank=True, null=True)
    Link_Hist_Mono = models.TextField(blank=True, null=True)
    Link_Hist_H2O = models.TextField(blank=True, null=True)    
    Link_Hist_EtOH = models.TextField(blank=True, null=True)
    Exp = models.ForeignKey(ExpBase, on_delete=models.CASCADE, blank=True, null=True)
    def __str__(self):
        return str(self.Name)

class OszAnalysisJoin(models.Model):
    """SEL Saves all dash properties of the SEL measurements

    Parameters
    ----------
    models : [type]
        [description]
    """    
    Name = models.TextField(unique=True, blank=True, null=True)
    OszAnalysis = models.ManyToManyField(OszAnalysis, blank=True)
    Dash = models.ForeignKey(OszAnalysis_dash, blank=True, on_delete=models.CASCADE)
    def __str__(self):
        return str(self.Name)
    def save(self, *args, **kwargs):#saves '' as none
         if not self.Name:
              self.Name = None
         super(OszAnalysisJoin, self).save(*args, **kwargs)

class DafAnalysis(models.Model):
    Name = models.TextField(unique=True, blank=True, null=True)
    Experiments = models.ManyToManyField(DAF, blank=True)
    def __str__(self):
        return str(self.Name)
    def save(self, *args, **kwargs):#saves '' as none
         if not self.Name:
              self.Name = None
         super(DafAnalysis, self).save(*args, **kwargs)
