
import sys
from typing import Generator

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

import json
import time
from youtube_dl import YoutubeDL


class ScrapeSubtitlesYtChannel:
    def __init__(self, channelUrl) -> None:
        ydl = YoutubeDL(
            {'ignoreerrors': True, 'extract_flat': 'in_playlist', 'dump_single_json': True})
        split = channelUrl.split('/')
        ydlChannel = ydl.extract_info(channelUrl, download=False)

        if split[-1] != "videos":
            sys.exit("Error: Please enter the channel's video page url")

        try:
            self.videosIds = [i['id'] for i in ydlChannel['entries']]
        except:
            print(
                "\nError: Youtube-dl tool struggled to get the channel's playlist - please input the playlist url"
            )
            ydlChannel = ydl.extract_info(input(), download=False)
            self.videosIds = [i['id'] for i in ydlChannel['entries']]

        self.channelName = channelUrl.split('/')[-2]
        self.baseYoutubeVidURL = "https://www.youtube.com/watch?v="
        self.startTime = time.time()


    def __enter__(self):
        """ Context manager """
        self.driver = webdriver.Chrome(
            executable_path=r'/usr/bin/chromedriver')
        self.wait = WebDriverWait(self.driver, 10)

        return self


    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """ Context manager """
        self.driver.close()
        ovTime = time.time() - self.startTime
        print("This channel has {} videos ".format(len(self.videosIds)))
        print("In {} mins".format(ovTime/60))

    def get_data_and_transcript(self, stopAtYear: int = None) -> Generator[str, str, str]:
        """Iterate through videos and grabs the transcript (if available, else "") and grabs the data through youtube-dl."""
        # videos = [(video.text, video.get_attribute("href"))
        #           for video in self.driver.find_elements_by_xpath('//*[@id="video-title"]') if video.text != ""]

        for id in self.videosIds:
            # Load video and bypass popups
            self.driver.get(self.baseYoutubeVidURL + id)
            self.youtube_account_popups()

            # grab transcript
            if self.open_transcript():
                self.check_if_english()
                transcript = "".join([i.text for i in self.driver.find_elements_by_xpath(
                    '//*[@id="body"]/ytd-transcript-body-renderer')])
            else:
                transcript = ""

            # Grab video info - fundamental metrics to a video
            video_info = self.get_video_information(id)

            # When the video cannot be accessed (e.g. paywall)
            if video_info is None:
                continue

            # Only want videos of data above given year
            if stopAtYear and int(video_info["date"][:4]) < stopAtYear:
                break

            yield transcript, video_info

    def youtube_account_popups(self) -> None:
        """ Closes youtube account popup if it comes """
        try:
            # 'no thanks'
            self.driver.implicitly_wait(2)
            self.driver.find_element(By.XPATH,
                                     "/html/body/ytd-app/ytd-popup-container/paper-dialog/yt-upsell-dialog-renderer/div/div[3]/div[1]/yt-button-renderer/a/paper-button/yt-formatted-string"
                                     ).click()

            # The second popup was a massive pain to get - learnt about iframes: https://www.guru99.com/handling-iframes-selenium.html
            iframe = self.wait.until(
                EC.element_to_be_clickable((By.TAG_NAME, "iframe")))

            self.driver.switch_to.frame(iframe)

            # 'i agree'
            self.wait.until(EC.element_to_be_clickable((By.XPATH,
                                                        "/html/body/div/c-wiz/div[2]/div/div/div/div/div[2]/form/div/span/span"))).click()
            self.driver.switch_to.parent_frame()

        except:
            # No popups -> can ignore. Had problem because i didn't explicitly go back into parent frame. Becareful of hidden bugs
            self.driver.switch_to.parent_frame()

    def get_video_information(self, id: str) -> dict:
        """Grabs title and video information via youtube-dl tool - avoids hassle of automating (this tool struggles with transcripts)"""
        # https://dokk.org/documentation/youtube-dl/2017.04.15/module_guide/
        ydl = YoutubeDL(
            {'ignoreerrors': True,
             'extract_flat': 'in_playlist',
             'dump_single_json': True}
        )

        extracted = ydl.extract_info(
            self.baseYoutubeVidURL + id, download=False)

        # return desired items
        try:
            return {
                "title": extracted["title"],
                "description": extracted["description"],
                "uploader": extracted["uploader"],
                "views": extracted["view_count"],
                "date": extracted["upload_date"],
                "like/dislike": [extracted["like_count"], extracted["dislike_count"]],
                "duration": extracted["duration"],
                "tags": extracted["tags"],
                "thumbnail": extracted["thumbnail"],
                "id": extracted["id"],
            }
        except:
            # When behind a paywall
            return None

    def open_transcript(self) -> bool:
        """Clicks on the menu and opens the transcript"""
        # Options button
        self.wait.until(EC.element_to_be_clickable(
            (By.XPATH,
                "//body/ytd-app/div[@id='content']/ytd-page-manager[@id='page-manager']/ytd-watch-flexy[@class='style-scope ytd-page-manager hide-skeleton']/div[@id='columns']/div[@id='primary']/div[@id='primary-inner']/div[@id='info']/div[@id='info-contents']/ytd-video-primary-info-renderer[@class='style-scope ytd-watch-flexy']/div[@id='container']/div[@id='info']/div[@id='menu-container']/div[@id='menu']/ytd-menu-renderer[@class='style-scope ytd-video-primary-info-renderer']/yt-icon-button[@id='button']/button[1]"
             ))
        ).click()

        # Open timestamps
        try:
            self.driver.implicitly_wait(1)
            timestamp_button = self.driver.find_element(
                By.CSS_SELECTOR, "#items > ytd-menu-service-item-renderer > paper-item")
            timestamp_button.click()
            return True
        except:
            return False

    def check_if_english(self):
        language = self.driver.find_element(
            By.XPATH, "/html/body/ytd-app/div/ytd-page-manager/ytd-watch-flexy/div[4]/div[1]/div/div[2]/ytd-engagement-panel-section-list-renderer/div[2]/ytd-transcript-renderer/div[3]/ytd-transcript-footer-renderer/div/yt-sort-filter-sub-menu-renderer/yt-dropdown-menu/paper-menu-button/div/paper-button/div")

        if "english" in language.text.lower():
            return
        else:
            language_options = self.driver.find_element(
                By.XPATH, "/html/body/ytd-app/div/ytd-page-manager/ytd-watch-flexy/div[4]/div[1]/div/div[2]/ytd-engagement-panel-section-list-renderer/div[2]/ytd-transcript-renderer/div[3]/ytd-transcript-footer-renderer/div/yt-sort-filter-sub-menu-renderer/yt-dropdown-menu/paper-menu-button/div/paper-button")
            language_options.click()
            # Naive assumption that english will be second - not great
            english_button = self.driver.find_element_by_xpath(
                "/html/body/ytd-app/div/ytd-page-manager/ytd-watch-flexy/div[4]/div[1]/div/div[2]/ytd-engagement-panel-section-list-renderer/div[2]/ytd-transcript-renderer/div[3]/ytd-transcript-footer-renderer/div/yt-sort-filter-sub-menu-renderer/yt-dropdown-menu/paper-menu-button/iron-dropdown/div/div/paper-listbox/a[2]/paper-item/paper-item-body/div[1]")
            english_button.click()


def main():
    if len(sys.argv) != 2:
        sys.exit("Error: invalid input. E.g. python file.py youtube_url")

    channel_url = sys.argv[1]

    """Creates json file for the videos: metrics and transcript."""
    with ScrapeSubtitlesYtChannel(channel_url) as scraper:

        with open(scraper.channelName + "_json.txt", 'w+') as json_file:
            for transcript, videoInfo in scraper.get_data_and_transcript(stopAtYear=2018):
                # For only videos from 2018 and older
                videoData = {
                    "meta": videoInfo,
                    "transcript": transcript,
                }
                json.dump(videoData, json_file)


if __name__ == "__main__":
    main()
