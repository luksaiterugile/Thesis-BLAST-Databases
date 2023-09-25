from django.contrib import admin
from .models import UserInput
from .models import BlastDBData
from .models import BlastnUserInput
from .models import BlastpUserInput
from .models import BlastnResults
from .models import BlastpResults
from .models import UpdateBlastDB
from .models import tBlastxUserInput, tBlastnUserInput, BlastxUserInput
from .models import tBlastxResults, tBlastnResults, BlastxResults
from .models import BatchAlign

class UserInputAdmin(admin.ModelAdmin):
    readonly_fields = ('created',)

class BlastnUserInputAdmin(admin.ModelAdmin):
    readonly_fields = ('created',)

class BlastpUserInputAdmin(admin.ModelAdmin):
    readonly_fields = ('created',)

class BlastxUserInputAdmin(admin.ModelAdmin):
    readonly_fields = ('created',)

class tBlastxUserInputAdmin(admin.ModelAdmin):
    readonly_fields = ('created',)

class tBlastnUserInputAdmin(admin.ModelAdmin):
    readonly_fields = ('created',)



admin.site.register(UserInput, UserInputAdmin)
admin.site.register(BlastDBData)
admin.site.register(BlastnUserInput, BlastnUserInputAdmin)
admin.site.register(BlastnResults)
admin.site.register(BlastpUserInput, BlastpUserInputAdmin)
admin.site.register(BlastpResults)
admin.site.register(BlastxUserInput, BlastxUserInputAdmin)
admin.site.register(BlastxResults)
admin.site.register(tBlastnUserInput, tBlastnUserInputAdmin)
admin.site.register(tBlastnResults)
admin.site.register(tBlastxUserInput, tBlastxUserInputAdmin)
admin.site.register(tBlastxResults)
admin.site.register(UpdateBlastDB)
admin.site.register(BatchAlign)
