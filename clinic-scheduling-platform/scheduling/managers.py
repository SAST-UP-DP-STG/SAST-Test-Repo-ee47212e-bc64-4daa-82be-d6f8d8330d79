from django.db import models


class EncounterQuerySet(models.QuerySet):
    def for_user(self, user):
        return self.filter(clinician=user)


class EncounterManager(models.Manager):
    def get_queryset(self):
        return EncounterQuerySet(self.model, using=self._db)

    def for_user(self, user):
        return self.get_queryset().for_user(user)
