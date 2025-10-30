from django.db import models

class test(models.Model):
    Name = models.TextField()

    def __str__(self):
        return str(self.Name)
