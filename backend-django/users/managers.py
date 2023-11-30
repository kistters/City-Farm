from django.contrib.auth.models import UserManager


class CitizenManager(UserManager):
    def get_queryset(self):
        return super(CitizenManager, self).get_queryset().filter(is_citizen=True)


class FarmerManager(UserManager):
    def get_queryset(self):
        return super(FarmerManager, self).get_queryset().filter(is_farmer=True)
