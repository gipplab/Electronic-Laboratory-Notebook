from Exp_Main.models import ExpPath
from Exp_Sub.models import ExpPath as ExpPathSub
def ExperimentTypes(request):
    ExperimentTypes = ExpPath.objects.all()

    return {
        'ExperimentTypes': ExperimentTypes,
    }
def SubExperimentTypes(request):
    SubExperimentTypes = ExpPathSub.objects.all()

    return {
        'SubExperimentTypes': SubExperimentTypes,
    }