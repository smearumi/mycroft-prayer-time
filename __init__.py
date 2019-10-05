# Copyright 2019 S. M. Estiaque Ahmed
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import requests
from subprocess import Popen
from datetime import datetime, timedelta
from adapt.intent import IntentBuilder
from mycroft.util.format import nice_time
from mycroft.util.time import now_local
from mycroft.util import get_cache_directory
from mycroft.skills.core import intent_handler
from mycroft.skills.common_play_skill import CommonPlaySkill, CPSMatchLevel


class PrayerTimeSkill(CommonPlaySkill):
    def __init__(self):
        super(PrayerTimeSkill, self).__init__(name="PrayerTimeSkill")
        self.prayer_times = None
        self.STREAM = '{0}/stream.mp3'.format(
                                        get_cache_directory("PrayerTimeSkill"))

        self.first_time_event_flag = True

    def initialize(self):
        self.handle_start_intent("start prayer time")

    def CPS_match_query_phrase(self, phrase):
        pass

    def CPS_start(self, phrase, data):
        pass

    @intent_handler(IntentBuilder("StartPrayerTimeIntent").require("Start")
                    .require("PrayerTime"))
    def handle_start_intent(self, message):
        if not self.first_time_event_flag:
            self.speak_dialog("status.mpt", {"status": "stop"})
            return

        else:
            self.speak_dialog("start.mpt")

        self.curl = None

        try:
            self.city = self.location['city']['state']['name']
            self.country = self.location['city']['state']['country']['name']
            self.method = str(self.settings.get("method"))
            self.school = str(self.settings.get("school"))
            adhan = str(self.settings.get("adhan"))

            if not self.city or not self.country or \
                    not self.method or not self.school or not adhan:
                raise Exception("None found.")

            self.adhan_url = "https://cdn.aladhan.com/"
            self.adhan_url = "{0}audio/adhans/{1}.mp3".format(
                                                            self.adhan_url,
                                                            adhan)

        except Exception:
            self.speak_dialog("settings.error")

        start_event = datetime.now()
        next_event = start_event.replace(
                                        hour=0,
                                        minute=1,
                                        second=0) + timedelta(days=1)
        self.interval = int((next_event - start_event).total_seconds())

        # self._schedule_event()
        self.cancel_scheduled_event(name="PrayerTime")

        self.schedule_repeating_event(
                                    self._schedule_event,
                                    start_event,
                                    self.interval,
                                    name="PrayerTime")

        # self.log.error(self.get_scheduled_event_status("PrayerTime"))

    @intent_handler(IntentBuilder("StopPrayerTimeIntent").require("Stop")
                    .require("PrayerTime"))
    def handle_stop_intent(self, message):
        if not self.first_time_event_flag:
            self.speak_dialog("status.mpt", {"status": "start"})
            return

        self.first_time_event_flag = True
        self.cancel_scheduled_event(name="PrayerTime")

        if self.prayer_times:
            for key, in self.prayer_times:
                self.cancel_scheduled_event(name="PrayerTime{0}".format(key))

        self.stop()
        self.speak_dialog("stop.mpt")

    @intent_handler(IntentBuilder("NextPrayerTimeIntent").require("Next")
                    .require("PrayerTime"))
    def handle_next_intent(self, message):
        if not self.prayer_times:
            return

        current_time = now_local()
        self.log.error(current_time)

        for key, value in self.prayer_times.items():
            if current_time < value:
                self.speak_dialog(
                                "next.mpt",
                                {"prayer": key,
                                 "time": nice_time(value, use_ampm=True)})
                break

    def _schedule_event(self):
        self.log.error("_schedule_event")
        self.log.error(self.get_scheduled_event_status("PrayerTime"))
        self.log.error(self.interval)

        if not self.first_time_event_flag and not self.interval == 86400:
            self.interval = 86400
            self.cancel_scheduled_event(name="PrayerTime")
            self.schedule_repeating_event(
                                        self._schedule_event,
                                        0,
                                        self.interval,
                                        name="PrayerTime")

        self.first_time_event_flag = False

        prayer_times = self.get_api_data()

        if prayer_times:
            self.prayer_times = prayer_times

        if not self.prayer_times:
            self.handle_stop_intent("stop prayer time")
            return

        current_time = now_local()
        self.log.error(current_time)

        for key, value in self.prayer_times.items():
            self.cancel_scheduled_event(name="PrayerTime{0}".format(key))

            if current_time < value:
                self.schedule_event(
                                self.play_adhan,
                                value,
                                name="PrayerTime{0}".format(key))

    def get_api_data(self):
        prayer_times = None

        api_url = "http://api.aladhan.com/v1/timingsByCity"
        api_url = "{0}?city={1}&country={2}&method={3}&school={4}".format(
                                                                api_url,
                                                                self.city,
                                                                self.country,
                                                                self.method,
                                                                self.school)

        try:

            api_headers = {'Content-Type': 'application/json',
                           'Accept': 'application/json'}

            response = requests.get(api_url, headers=api_headers)

            if response.status_code == 200:
                prayer_times = response.json()['data']['timings']

            else:
                return None

        except Exception:
            return None

        fajr = datetime.strptime(prayer_times['Fajr'], "%H:%M")
        dhuhr = datetime.strptime(prayer_times['Dhuhr'], "%H:%M")
        asr = datetime.strptime(prayer_times['Asr'], "%H:%M")
        maghrib = datetime.strptime(prayer_times['Maghrib'], "%H:%M")
        isha = datetime.strptime(prayer_times['Isha'], "%H:%M")

        # fajr = datetime.strptime("04:20", "%H:%M")
        # dhuhr = datetime.strptime("04:27", "%H:%M")
        # asr = datetime.strptime("05:10", "%H:%M")
        # maghrib = datetime.strptime("05:12", "%H:%M")
        # isha = datetime.strptime("05:15", "%H:%M")

        current_time = datetime.now()

        fajr = fajr.replace(
                        year=current_time.year,
                        month=current_time.month,
                        day=current_time.day)

        dhuhr = dhuhr.replace(
                        year=current_time.year,
                        month=current_time.month,
                        day=current_time.day)

        asr = asr.replace(
                        year=current_time.year,
                        month=current_time.month,
                        day=current_time.day)

        maghrib = maghrib.replace(
                        year=current_time.year,
                        month=current_time.month,
                        day=current_time.day)

        isha = isha.replace(
                        year=current_time.year,
                        month=current_time.month,
                        day=current_time.day)

        prayer_times = {'Fajr': fajr,
                        'Dhuhr': dhuhr,
                        'Asar': asr,
                        'Maghreeb': maghrib,
                        'Isha': isha}

        # prayer_times = {'Fajr': 5,
        #                 'Dhuhr': 10,
        #                 'Asar': 15,
        #                 'Maghreeb': 20,
        #                 'Isha': 25}

        return prayer_times

    def play_adhan(self):
        self.log.error(self.get_scheduled_event_status("PrayerTime"))
        self.curl = None

        if os.path.exists(self.STREAM):
            os.remove(self.STREAM)

        os.mkfifo(self.STREAM)

        self.curl = Popen(
                        'curl -L "{}" > {}'.format(
                                                self.adhan_url,
                                                self.STREAM),
                        shell=True)

        self.CPS_play(("file://" + self.STREAM, "audio/mpeg"))
        self.log.error("Ajaan played!!!")

    def stop(self):
        self.log.error("Stop PrayerTime")

        if self.curl:
            try:
                self.curl.kill()
                self.curl.communicate()

            except Exception:
                pass

            finally:
                self.curl = None

            return True


def create_skill():
    return PrayerTimeSkill()
