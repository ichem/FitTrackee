from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.conf import settings
from django.db import transaction

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import authentication, permissions

from .models import Activity, Gpx, Sport
from ..user.models import User
from .forms import AddActivityForm
from .utils import gpx_info

from datetime import timedelta
import pandas


@login_required
def add_activity(request):
    if request.method == 'POST':
        form = AddActivityForm(request.POST, request.FILES)
        if form.is_valid():

            try:
                with transaction.atomic():
                    user = User.objects.get(username=request.user.username)
                    sport = Sport.objects.get(pk=request.POST['sport'])

                    new_gpx = Gpx()
                    new_gpx.gpx_file = request.FILES['gpx_file']
                    new_gpx.save()

                    gpx_data = gpx_info(settings.MEDIA_ROOT + '/' + str(new_gpx.gpx_file))

                    new_activity = Activity()
                    new_activity.user = user
                    new_activity.sport = sport
                    new_activity.gpx = new_gpx
                    new_activity.activity_date = gpx_data['start']
                    new_activity.duration = timedelta(seconds=gpx_data['duration'])
                    new_activity.pauses = timedelta(seconds=gpx_data['stop_time'])
                    new_activity.moving = timedelta(seconds=gpx_data['moving_time'])
                    new_activity.distance = gpx_data['distance']
                    new_activity.min_alt = gpx_data['elevation_min']
                    new_activity.max_alt = gpx_data['elevation_max']
                    new_activity.descent = gpx_data['downhill']
                    new_activity.ascent = gpx_data['uphill']
                    new_activity.max_speed = gpx_data['max_speed']
                    new_activity.ave_speed = gpx_data['average_speed']

                    new_activity.save()

                    return redirect('/activities/' + str(new_activity.id))

            except Exception as e:
                print(e)
                err_msg = 'An error occurred, please retry'
                return render(request, 'activities/add_activity.html',
                              {'form': form, 'error': err_msg})

    else:
        form = AddActivityForm()
    return render(request, 'activities/add_activity.html', {'form': form})


@login_required
def display_activity(request, activity_id):
    activity = get_object_or_404(Activity, pk=activity_id)
    gpx_file = Gpx.objects.all().get(id=activity.gpx_id).gpx_file
    gpx = str(gpx_file)
    return render(request, 'activities/display_activity.html', {'activity': activity, 'gpx':  gpx})


@login_required
def display_activities(request):
    activities = Activity.objects.all().order_by('-activity_date').filter(
        user_id=request.user.id)[:10]
    return render(request, 'activities/display_activities.html', {'activities': activities})


# API
#####

class UserActivitiesList(APIView):

    authentication_classes = (authentication.SessionAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request):
        # labels = [sport.label for sport in Sport.objects.all()]

        color = ['rgba(151,187,205,0.2)', 'rgba(247,70,74,0.2)', 'rgba(148,159,177,0.2)',
                 'rgba(70,191,189,0.2)', 'rgba(253,180,92,0.2)']
        color_border = ['blue', 'red', 'grey', 'green', 'yellow']
        activities_df = pandas.DataFrame([(activity.activity_date, activity.sport.label) for
                                          activity in Activity.objects.all().order_by('-activity_date').filter(
                                          user_id=request.user.id)[:10]], columns=['Date', 'Sport'])

        sports_list = activities_df.Sport.unique()
        labels_date = activities_df.Date
        activities_data = []
        i = 0

        for sport in sports_list:
            activities_df[sport] = activities_df.Sport.str.extract("(" + sport + ")", expand=False)
            activities_df[sport] = activities_df[sport].str.replace("(" + sport + ")", "1")
            data_list = activities_df[sport].tolist()
            data_list = [1 if x == '1' else 0 for x in data_list]
            temp_dict = {
                'label': sport,
                'backgroundColor': color[i],
                'borderColor': color_border[i],
                'borderWidth': 1,
                'data': data_list
            }
            activities_data.append(temp_dict)
            i += 1
            if i > 4:
                i = 0

        data = {
            "labels": labels_date,
            "activities": activities_data
        }
        return Response(data)
