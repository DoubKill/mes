from django.contrib import admin

# Register your models here.


from terminal.models import Terminal, TerminalLocation, Version, WeightTankStatus
admin.site.register([Terminal, TerminalLocation, Version, WeightTankStatus])