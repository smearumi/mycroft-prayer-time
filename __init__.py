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
from datetime import datetime
from adapt.intent import IntentBuilder
from mycroft.util import get_cache_directory
from mycroft.skills.core import intent_handler
from mycroft.skills.common_play_skill import CommonPlaySkill, CPSMatchLevel

direct_play_filetypes = [".mp3"]


class PrayerTimeSkill(CommonPlaySkill):
    def __init__(self):
        super(PrayerTimeSkill, self).__init__(name="PrayerTimeSkill")

        self.curl = None
        self.now_playing = None
        self.STREAM = '{0}/stream.mp3'.format(
                                    get_cache_directory("PrayerTimeSkill"))

    def CPS_match_query_phrase(self, phrase):
        self.log.error("CPS MATCH")
        phrase = ' '.join(phrase.lower().split())

        self.log.error(phrase)

        if self.voc_match(phrase, "PrayerTime"):
            return ("PrayerTime", CPSMatchLevel.TITLE)

    def CPS_start(self, phrase, data):
        self.log.error("CPS START")
        self.handle_start_intent()

    @intent_handler(IntentBuilder("StartPrayerTimeIntent").require("Start")
                    .require("PrayerTime"))
    def handle_start_intent(self, message):
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

            self._schedule_event()

        except Exception as e:
            self.speak_dialog("settings.error")
            self.log.error(e)

    @intent_handler(IntentBuilder("StopPrayerTimeIntent").require("Stop")
                    .require("PrayerTime"))
    def handle_stop_intent(self, message):
        try:
            self.log.error(self.get_scheduled_event_status("PrayerTime"))
            self.cancel_scheduled_event(name="PrayerTime")

        except Exception:
            pass

    def _schedule_event(self):
        try:
            self.remove_event(name="PrayerTime")
            self.log.error(self.get_scheduled_event_status(name="PrayerTime"))
            self.cancel_scheduled_event(name="PrayerTime")

        except Exception as e:
            self.log.error("ERRORRRR")
            self.log.error(e)
            pass

        prayer_times = self.get_api_data()

        if prayer_times:
            self.prayer_times = prayer_times

        current_time = datetime.now()

        for key, value in self.prayer_times.items():
            if current_time <= value:
                break

        self.log.error(value)
        self.schedule_event(self.play_adhan, value, name="PrayerTime")
        self.log.error(self.get_scheduled_event_status("PrayerTime"))
        self.log.error(value)

    def get_api_data(self):
        prayer_times = None

        try:
            api_url = "http://api.aladhan.com/v1/timingsByCity"
            api_url = "{0}?city={1}&country={2}&method={3}".format(
                                                                api_url,
                                                                self.city,
                                                                self.country,
                                                                self.method)

            api_headers = {'Content-Type': 'application/json',
                           'Accept': 'application/json'}

            response = requests.get(api_url, headers=api_headers)

            if response.status_code == 200:
                prayer_times = response.json()['data']['timings']

            else:
                return None

        except Exception as e:
            self.log.error(e)
            return None

        # fajr = datetime.strptime(prayer_times['Fajr'], "%H:%M")
        # dhuhr = datetime.strptime(prayer_times['Dhuhr'], "%H:%M")
        # asr = datetime.strptime(prayer_times['Asr'], "%H:%M")
        # maghrib = datetime.strptime(prayer_times['Maghrib'], "%H:%M")
        # isha = datetime.strptime(prayer_times['Isha'], "%H:%M")

        fajr = datetime.strptime("19:40", "%H:%M")
        dhuhr = datetime.strptime("19:41", "%H:%M")
        asr = datetime.strptime("19:42", "%H:%M")
        maghrib = datetime.strptime("19:43", "%H:%M")
        isha = datetime.strptime("19:44", "%H:%M")

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

        prayer_times = {'fajr': fajr,
                        'dhuhr': dhuhr,
                        'asr': asr,
                        'maghrib': maghrib,
                        'isha': isha}

        return prayer_times

    def play_adhan(self):
        self.curl = None

        # if os.path.exists(self.STREAM):
        #     os.remove(self.STREAM)

        # os.mkfifo(self.STREAM)

        # self.curl = Popen(
        #                 'curl -L "{}" > {}'.format(
        #                                         self.adhan_url,
        #                                         self.STREAM),
        #                 shell=True)

        # self.CPS_play(("file://" + self.STREAM, "audio/mpeg"))
        self._schedule_event()
        self.log.error("Ajaan played!!!")

    def stop(self):
        self.log.error("Stop")
        if self.curl:
            try:
                self.curl.kill()
                self.curl.communicate()

            except Exception as e:
                self.log.error('Could not stop curl: {}'.format(repr(e)))

            finally:
                self.curl = None

            return True


def create_skill():
    return PrayerTimeSkill()
