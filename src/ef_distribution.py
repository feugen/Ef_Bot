import src.ef_connector as ef_connection
import src.ef_rating as ef_rating
import src.ef_functions as ef_functions
import src.ef_subscription as ef_subscribtion
import os
import threading
import time
import sys
import datetime
from apiclient import errors
import ipaddress


class Distribution:

    def __init__(self):

        # Connector instance
        self.inst_conn = ef_connection.Connector()

        # Hilfsfunktion_yt instance
        self.inst_helpfct = ef_functions.Hilfsfunktionen_yt()

        # Rating instance
        self.inst_rating = ef_rating.Rating()

        # Subscription instance
        self.inst_subscr = ef_subscribtion.Subscription()

        # Add watching instance when completed

    daytime_factor = None

    def get_accounts_number(self):

        account_dir = './acc'
        accounts = os.listdir(account_dir)
        accounts.sort()

        accounts_number = int(accounts[-1])

        if len(accounts) != accounts_number:
            print(self.inst_helpfct.timestamp() + 'Distribution::get_accounts_number: Attention, number of account'
                  ' directories dont match the max directory number')

        oauth_file = 'oauth2.json'

        for i in accounts:
            oauth_path = account_dir + '/' + str(i) + '/' + oauth_file
            if not os.path.exists(oauth_path):
                print(self.inst_helpfct.timestamp() + 'Distribution::get_accounts_number: Attention, oauth2 file'
                      ' is missing in directory {0} Not yet signed in?'.format(i))

        return accounts_number

    def get_proxy_list(self, proxy_type):

        f = None

        if proxy_type == 'http':
            f = open('proxy_http_ip.txt', mode='r')
        elif proxy_type == 'socks5':
            f = open('proxy_socks_auth.txt', mode='r')

        proxy_array = []

        proxy_file = f.readlines()

        for line in proxy_file:
            if line != '\n':
                port_position = -1
                char = line[port_position]
                while char is not ':':
                    port_position -= 1
                    char = line[port_position]
                    if port_position == -100:
                        print('Distribution::get_proxy_list: '
                              'something wrong in proxy file? To many characters in line?')
                        break
                port_number = line[port_position+1:-1]
                port_ip = line[0:port_position]
                # Check if IP Address is valid
                ip = None
                try:
                    ip = ipaddress.ip_address(port_ip)
                except ValueError:
                    print('Distribution::get_proxy_list: IP ' + str(ip) + 'seems not to be valid')
                tuple_array = [port_ip, port_number]
                proxy_array.append(tuple_array)

        return proxy_array

    def dynamic_threads_number(self, threads_number_max):

        current_time = datetime.datetime.now().time()

        morning_start = datetime.time(6, 0, 0)
        midday_start = datetime.time(12, 0, 0)
        evening_start = datetime.time(17, 0, 0)
        night_start = datetime.time(23, 0, 0)

        if morning_start <= current_time <= midday_start:
            self.daytime_factor = 0.4
        elif midday_start <= current_time <= evening_start:
            self.daytime_factor = 0.6
        elif evening_start <= current_time <= night_start:
            self.daytime_factor = 1
        else:
            self.daytime_factor = 0

        return int(threads_number_max*self.daytime_factor)


class Distribution_yt(Distribution):

    def thread_rating(self, account_nr, proxy_host, proxy_port, proxy_type, auto_video, max_history_sites=1,
                      one_shot_channel_id=None, one_shot_video_id=None, one_shot_reason=1, thread_name=None):

        if one_shot_video_id is not None and one_shot_channel_id is not None:
            sys.exit(self.inst_helpfct.timestamp() + 'Distribution::thread_rating: At least two one'
                                                     ' shot parameters were provided,'
                     ' for channel and video. Pls provide only one parameter at the time.')

        yt_handle = None

        try:
            yt_handle = self.inst_conn.yt_connection(account_nr, proxy_host, proxy_port, proxy_type)
        except errors.HttpError as e:
            print(self.inst_helpfct.timestamp() + 'Distribution::thread_rating: '
                                                  'Something went wrong, yt_handle not created? An HTTP '
                  'error {0} occurred:\n{1}'.format(e.resp.status, e.content))

        # Channel_list_by_id and video_list_by_channel have the same order
        # its needed for Rating.youtube_channel function to verify if to rate up or down
        if one_shot_channel_id is None:
            channel_list_by_id = self.inst_helpfct.get_channel_list_from_sqlite()
        else:
            channel_list_by_id = [[one_shot_channel_id, one_shot_reason]]

        # If just a video is provided, so rate the video.
        if one_shot_video_id is not None:
            rating = None
            if one_shot_reason == 1:
                rating = 'like'
            elif one_shot_reason == 0:
                rating = 'dislike'
            else:
                print(self.inst_helpfct.timestamp() + 'Distribution::thread_rating: '
                                                      'Attention, reason argument is not 1 or 0')
            self.inst_rating.youtube_video_manual(yt_handle, one_shot_video_id, rating)
        # If its not the case, than a channel or auto channel from db is wished
        else:
            # print(channel_list_by_id)
            video_list_by_channel = self.inst_helpfct.video_id_list_by_channel(yt_handle, channel_list_by_id,
                                                                               max_history_sites)

            # If auto_video is enabled, then call additional youtube_video_auto function
            # its rating the videos from db
            if auto_video:
                self.inst_rating.youtube_video_auto(yt_handle, thread_name)

            # print(video_list_by_channel)
            self.inst_rating.youtube_channel_auto(yt_handle, video_list_by_channel, channel_list_by_id, thread_name)

        return 0

    def thread_subscription(self, account_nr, proxy_host, proxy_port, proxy_type, one_shot_subscription):

        yt_handle = None

        try:
            yt_handle = self.inst_conn.yt_connection(account_nr, proxy_host, proxy_port, proxy_type)
        except errors.HttpError as e:
            print(self.inst_helpfct.timestamp() + 'Distribution::thread_subscription: '
                                                  'Something went wrong, yt_handle not created? An HTTP '
                  'error {0} occurred:\n{1}'.format(e.resp.status, e.content))

        try:
            channel_title = self.inst_subscr.add_subscription_yt(yt_handle, one_shot_subscription)
        except errors.HttpError as e:
            print(self.inst_helpfct.timestamp() + "Distribution::thread_subscription: "
                                                  "An HTTP error {0} occurred:\n{1}".format(e.resp.status, e.content))
        else:
            print(self.inst_helpfct.timestamp() + "Distribution::thread_subscription: "
                                                  "A subscription to {0} was added.".format(channel_title))

    def run(self, threads_number_max, threads_dynamic, accounts_number_to_use, max_history_sites,
            auto_video, one_shot_channel_id, one_shot_video_id_or_link, one_shot_reason,
            one_shot_subscription, proxy_type):

        # Check and print the mode
        if one_shot_channel_id is None and one_shot_video_id_or_link is None:
            print(self.inst_helpfct.timestamp() + 'Distribution::run: auto-channel-mode was started, '
                                                  'since no one-shot channel or video provided')
        elif one_shot_channel_id is None and one_shot_video_id_or_link is not None:
            print(self.inst_helpfct.timestamp() + 'Distribution::run: one shot video mode was started')
        elif one_shot_channel_id is not None and one_shot_video_id_or_link is None:
            print(self.inst_helpfct.timestamp() + 'Distribution::run: one shot channel mode was started')
        if auto_video:
            print(self.inst_helpfct.timestamp() + 'Distribution::run: Additionally auto_video'
                                                  ' (lonely videos from db) was started')

        one_shot_video_id = None

        if one_shot_video_id_or_link is not None:
            # Check for a proper video_id, if its a link, extract it from the link
            one_shot_video_id = self.inst_helpfct.get_yt_video_id_from_link(one_shot_video_id_or_link)

            # Check if channel_id and video_id are both provided, if its the case, raise an error, because only
            # one parameter can be passed. As video_id already checked, check for channel_id

            if one_shot_channel_id is not None:
                sys.exit(self.inst_helpfct.timestamp() + 'Distribution::run: '
                                                         'At least two one shot parameters were provided,'
                         ' for channel and video. Pls provide only one parameter at the time.')

        if accounts_number_to_use is None:
            accounts_number_to_use = self.get_accounts_number()

        # Get proxy list with ports
        proxy_list = self.get_proxy_list(proxy_type)

        if accounts_number_to_use > len(proxy_list):
            print(self.inst_helpfct.timestamp() + 'Distribution::run: Attention, '
                                                  'Accounts number is higher than Proxy number.'
                  ' Strange behavior or crash is possible when arguments passed to thread_rating function')

        # Now create a handle for each account number and proxy
        # because of the range increase the account number by 1
        for account_nr in range(1, accounts_number_to_use+1):
            # Get proxy_host and proxy_port
            proxy_host = proxy_list[account_nr-1][0]
            proxy_port = proxy_list[account_nr-1][1]

            thread_name = 'Thread_' + str(account_nr)
            # No one_shot_subscription means rating
            thread = None

            if one_shot_subscription is None:
                thread = threading.Thread(target=self.thread_rating, name=thread_name,
                                          args=(account_nr, proxy_host, proxy_port, proxy_type,
                                                max_history_sites, auto_video, one_shot_channel_id,
                                                one_shot_video_id, one_shot_reason, thread_name))

            if one_shot_subscription is not None:
                thread = threading.Thread(target=self.thread_subscription, name=thread_name,
                                          args=(account_nr, proxy_host, proxy_port, proxy_type, one_shot_subscription))

            thread.start()
            print(self.inst_helpfct.timestamp() + 'Distribution::run: ' + thread.getName() + ' was started')
            number_of_threads = len(threading.enumerate())

            # For some reason we have to slow down threads starting, or we will get different ssl errors
            time.sleep(1)

            # Check how many threads are currently running
            # Minus 1 is needed, because main thread is counted as well

            if threads_dynamic:
                threads_number_dynamic = self.dynamic_threads_number(threads_number_max)
            else:
                threads_number_dynamic = threads_number_max
            print(self.inst_helpfct.timestamp() + 'Distribution::run: current max'
                                                  ' possible threads (dynamic): {0}'.format(threads_number_dynamic))

            while number_of_threads-1 > threads_number_dynamic:
                sleeping_time = 300
                print(self.inst_helpfct.timestamp() + 'Distribution::run: Max number of threads is reached.'
                      ' Wait for {0} seconds for some threads to finish before new assignment. Current'
                      ' active threads are {1}'.format(sleeping_time, threading.enumerate()))
                time.sleep(sleeping_time)
                number_of_threads = len(threading.enumerate())

        # Cant use thread.join because its not reachable since its in a loop
        # Wait till all threads are finished before continue
        while len(threading.enumerate()) > 1:
            sleeping_time = 600
            print(self.inst_helpfct.timestamp() + 'Main thread is waiting for {1} threads to finish,'
                  ' next check in {0} seconds'.format(sleeping_time, len(threading.enumerate()) - 1))
            time.sleep(sleeping_time)
        print(self.inst_helpfct.timestamp() + 'Distribution::run: Main thread finished')
