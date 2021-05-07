from django.db import models
from datetime import datetime
from mptt.models import MPTTModel, TreeForeignKey, TreeManyToManyField

# Create your models here.
class ProjectEntry(models.Model):
    Name = models.TextField(db_column='Name:', unique=True, blank=True, null=True)
    Description = models.TextField(db_column='Description:', blank=True, null=True)
    Conclusion = models.TextField(db_column='Conclusion:', blank=True, null=True)
    Issued = models.DateTimeField(default=datetime.now, blank=True)
    DueDate = models.DateTimeField(default=datetime(2023, 12, 31, 0, 0, 0), blank=True)
    Fineshed = models.BooleanField('Fineshed:')
    def __str__(self):
        return str(self.Name)

class Project(MPTTModel):
    Name = models.TextField(db_column='Name:', unique=True, blank=True, null=True)  # Field name made lowercase. Field renamed to remove unsuitable characters. Field renamed because it ended with '_'.
    Description = models.TextField(db_column='Description:', blank=True, null=True)  # Field name made lowercase. Field renamed to remove unsuitable characters. Field renamed because it ended with '_'.
    parent = TreeForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='children')
    Issued = models.DateTimeField(default=datetime.now, blank=True)
    DueDate = models.DateTimeField(default=datetime(2023, 12, 31, 0, 0, 0), blank=True)
    Fineshed = models.BooleanField('Fineshed:')
    PossiblePrios = [('1', 'Critical'), ('2', 'High'), ('3', 'Medium'), ('4', 'Low')]
    Priory = models.CharField(max_length=1, choices=PossiblePrios, default='3')
    Entry = models.ManyToManyField(ProjectEntry, blank=True)
    class MPTTMeta:
        order_insertion_by = ['Name']
    def __str__(self):
        return str(self.Name)

class SampleBase(MPTTModel):
    """SampleBase Model to store all the samples in

    Parameters
    ----------
    models : [type]
        [description]

    Returns
    -------
    str
        Name of sample
    """    
    Name = models.TextField(unique=True)
    Comment = models.TextField(blank=True, null=True)
    parent = TreeForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='children')

    def __str__(self):
        return str(self.Name)

class Polymer(models.Model):
    """Polymer Model to store all polymers in

    Parameters
    ----------
    models : [type]
        [description]

    Returns
    -------
    str
        Name of polymer
    """    
    Name = models.TextField(unique=True)
    Material = models.TextField(blank=True, null=True)
    Manufactured = models.DateTimeField(default=datetime(1900, 1, 1, 0, 0, 0), blank=True)
    Manufacturer = models.TextField(blank=True, null=True)
    Number_average_kDa = models.FloatField(blank=True, null=True)
    Weight_average_kDa = models.FloatField(blank=True, null=True)
    def __str__(self):
        return str(self.Name)

class PseudoSample(SampleBase):
    def __str__(self):
        return str(self.Name)
class SampleBrushPNiPAAmSi(SampleBase):
    """SampleBrushPNiPAAmSi Model to store all samples that are a PNiPAAm brush and grafted to silica

    Parameters
    ----------
    SampleBase : Model
        :py:meth:`SampleBase`

    Returns
    -------
    str
        Name of sample
    """    
    Parent = models.TextField(blank=True, null=True)
    Birth = models.DateTimeField(default=datetime(1900, 1, 1, 0, 0, 0), blank=True)
    Death = models.DateTimeField(default=datetime(1900, 1, 1, 0, 0, 0), blank=True)
    Length_cm = models.FloatField(blank=True, null=True)
    Width_cm = models.FloatField(blank=True, null=True)
    Thickness_SiO2_nm = models.FloatField(blank=True, null=True)
    Thickness_PGMA_nm = models.FloatField(blank=True, null=True)
    Thickness_PNiPAAm_nm = models.FloatField(blank=True, null=True)
    Number_on_back = models.IntegerField(blank=True, null=True)
    Polymer = models.ManyToManyField(Polymer, blank=True)
    def __str__(self):
        return str(self.Name)

class SampleBrushPNiPAAmInfasil(SampleBase):
    """SampleBrushPNiPAAmSi Model to store all samples that are a PNiPAAm brush and grafted to silica

    Parameters
    ----------
    SampleBase : Model
        :py:meth:`SampleBase`

    Returns
    -------
    str
        Name of sample
    """    
    Parent = models.TextField(blank=True, null=True)
    Birth = models.DateTimeField(default=datetime(1900, 1, 1, 0, 0, 0), blank=True)
    Death = models.DateTimeField(default=datetime(1900, 1, 1, 0, 0, 0), blank=True)
    Diameter_cm = models.FloatField(blank=True, null=True)
    Thickness_PGMA_nm = models.FloatField(blank=True, null=True)
    Thickness_PNiPAAm_nm = models.FloatField(blank=True, null=True)
    Number_on_back = models.IntegerField(blank=True, null=True)
    Polymer = models.ManyToManyField(Polymer, blank=True)
    def __str__(self):
        return str(self.Name)

class SamplePseudoBrushPDMSGlass(SampleBase):
    """SamplePseudoBrushPDMSGlass Model to store all samples that are a pseudo PDMS brush and grafted to glass

    Parameters
    ----------
    SampleBase : Model
        :py:meth:`SampleBase`

    Returns
    -------
    str
        Name of sample
    """    
    Parent = models.TextField(blank=True, null=True)
    Birth = models.DateTimeField(default=datetime(1900, 1, 1, 0, 0, 0), blank=True)
    Death = models.DateTimeField(default=datetime(1900, 1, 1, 0, 0, 0), blank=True)
    Length_cm = models.FloatField(blank=True, null=True)
    Width_cm = models.FloatField(blank=True, null=True)
    Thickness_PDMS_nm = models.FloatField(blank=True, null=True)
    Polymer = models.ManyToManyField(Polymer, blank=True)
    def __str__(self):
        return str(self.Name)

class SampleBlank(SampleBase):
    """SampleBlank Model to store Samples without anything on top

    Parameters
    ----------
    SampleBase : Model
        :py:meth:`SampleBase`

    Returns
    -------
    str
        Name of sample
    """    
    Material = models.TextField(blank=True, null=True)
    Description = models.TextField(blank=True, null=True)
    Length_cm = models.FloatField(blank=True, null=True)
    Width_cm = models.FloatField(blank=True, null=True)
    def __str__(self):
        return str(self.Name)