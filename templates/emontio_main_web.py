#!/usr/bin/python

import json
import pandas as pd
import numpy as np
import os
import argparse
import logging
import logging.handlers
from watson_developer_cloud import ToneAnalyzerV3, AlchemyDataNewsV1, AlchemyLanguageV1
from alchemyapi import AlchemyAPI
from os.path import join, dirname
import collections
import newspaper
from newspaper import Article, Source, Config
import requests
from flask import Flask
#import cf_deployment_tracker
import cgi
import sys
from datetime import datetime
import time


# Error: the results of Tone Analyzer are different from the original website.


# Object to scan files that contain news
class Emontio_Analyzer(object):
    """ Scans files to see which ones are relevant stock_id """


    def __init__(self, stock_id, stock_name, web_url):
        """ object """
        self.stock_id = stock_id
        self.stock_name = stock_name
        self.web_url = web_url
        self.targeted_paragraphs = []
        self.targeted_urls = []
        self.article_url = []
        self.article_title = []

        self.list_time_elapsed = []

        self.json_results = []
        self.json_to_html = []


        #self.result_tone_reader_json = [] ######## Alternative data format
        self.list_df_html = [] ##############


        #**** Lists of results: ****
        self.result_scan_web = {}
        self.list_df_html = [] ##############
        self.result_tone_reader = []
        self.result_entity_extraction = []
        self.result_sentiment_analysis = []




    def get_api_key(self):

        # Open the key file and read the key
        print "--------------------------------"
        print "Retrieving API keys..."
        with open('templates/watson_credentials.json', 'r') as f:
            self.watson_credentials = json.load(f)

        if not self.watson_credentials['username'] or not self.watson_credentials['password']:
            # The key file should't be blank
            print 'Error: valid username/password not found.'
            sys.exit(1)
        print "API keys are retrieved."


    def scan_targeted_web(self):

        print " -------------------------------"
        print "# SCANNING TARGETED WEBPAGE:"
        print " -------------------------------"

        print "Targeted Webpage: " , self.web_url

        startTime = datetime.now()

        targeted_webpage = newspaper.build(self.web_url, language = 'en', memoize_articles = False , fetch_images = False)

        # Targets an individual article.
        #targeted_article = Article(url = self.web_url, config)

        print "Number of articles in %s" % self.web_url ," = " , targeted_webpage.size()
        print "URLs: "

        self.result_scan_web["targeted_webpage"] = self.web_url;
        self.result_scan_web["article_count"] = targeted_webpage.size()

        count = 0
        while True :
            for article in targeted_webpage.articles:
                print article.url
                self.targeted_urls.append(article.url)

                print "Downloading the article:"
                article.download()

                try:
                    print "Parsing the article paragraph from HTML..."
                    article.parse()
                except:
                    pass

                print "Extracting the paragraph..."
                paragraph = article.text

                print "Extraction is completed."

                if self.stock_id in paragraph or self.stock_name in paragraph:
                    self.targeted_paragraphs.append(paragraph)
                    self.article_url.append(article.url)
                    self.article_title.append(article.title)
                    print "SUCCESS: " , article.url

                    successful_articles_json = {"Successful Articles" : article.url}
                    self.json_results.append(successful_articles_json)

                count = count + 1

                print  "COUNT: " , count , " != " , targeted_webpage.size()

                if count == targeted_webpage.size():
                    print count , " == " , targeted_webpage.size()
                    print "Entire articles at the targeted webpage is read, downloaded, parsed and paragraphs are extracted."
                    print "Time Elapsed: " , datetime.now() - startTime
                    execution_time = datetime.now() - startTime
                    self.list_time_elapsed.append(execution_time)
                    break

                else:

                    print "SCANNING..."

                    continue

            return self.targeted_paragraphs
            return self.targeted_urls

    def Tone_Reader(self):

        print " ----------------------------"
        print "# STARTING TONE ANALYZER:"
        print " ----------------------------"
        print "Number of Successful Articles = " , len(self.article_url)
        print "SUCCESSFUL URLs: " ,
        for article in self.article_url:
            print article

        startTime = datetime.now()
        data_frames = []
        count = 0

        for paragraph in self.targeted_paragraphs :
            print "Reading the extracted articles..."
            if (self.stock_id + " ") in paragraph or (self.stock_name + " " ) in paragraph:

                # Starting IBM WATSON Tone Analyzer Service. Makes an API call for each successful filename.
                tone_analyzer = ToneAnalyzerV3(
                    username= self.watson_credentials['username'] ,
                    password= self.watson_credentials['password'],
                    version='2016-02-11')
                print "Tone Analyzer is initiated."

                # DOCUMENT TONE: Extracts columns to prepare numbers
                results = tone_analyzer.tone(text=paragraph)

                #result_in_json = json.dumps(tone_analyzer.tone(text=paragraph) , indent=2)
                # Gives out original JSON format as it is sent from IBM WATSON API
                #self.result_tone_reader_json.append(result_in_json)
                #print result_in_json


                emotion_tone = results["document_tone"]["tone_categories"][0]["tones"]
                writing_tone = results["document_tone"]["tone_categories"][1]["tones"]
                social_tone = results["document_tone"]["tone_categories"][2]["tones"]

                # DOCUMENT TONE: Prepares the dataframe for each tone category.
                print "Preparing results..."
                df_emotion_tone = pd.DataFrame(emotion_tone)
                df_writing_tone = pd.DataFrame(writing_tone)
                df_social_tone = pd.DataFrame(social_tone)



                # DOCUMENT TONE:  Analyzes the tone score for emotion, writing, and social.
                # emotion_tone
                less_emotion = df_emotion_tone.loc[df_emotion_tone.score <= 0.5] # Less likely to be perceived.
                high_emotion = df_emotion_tone.loc[df_emotion_tone.score >= 0.75] # High likely to be perceived.

                # writing_tone
                less_writing = df_writing_tone.loc[df_writing_tone.score <= 0.25] # Less likely to be perceived.
                high_writing = df_writing_tone.loc[df_writing_tone.score >= 0.75] # High likely to be perceived.

                # social_tone
                less_social = df_social_tone.loc[df_social_tone.score <= 0.25] # Less likely to be perceived.
                high_social = df_social_tone.loc[df_social_tone.score >= 0.75] # High likely to be perceived.



                # DataFrame High likely
                high_likely_frame = pd.concat([high_emotion, high_writing, high_social])

                # DataFrame Less Likely
                less_likely_frame = pd.concat([less_emotion, less_writing, less_social])


                # Combines the dataframes for all categories.
                df_combine = pd.concat([df_emotion_tone , df_writing_tone]) # -> adds side by side.
                full_df = pd.concat([df_combine , df_social_tone])

                print "DOCUMENT-LEVEL RESULTS:  "

                print "ARTICLE TITLE: " , self.article_title[len(self.article_title) - len(self.article_title) + count]
                print 'ARTICLE URL: ' , self.article_url[len(self.article_url) - len(self.article_url) + count]
                print "DATA FRAME: "
                #print full_df

                count = count + 1
                data_frames.append(full_df)

                # Creates .csv results file for each file
                #full_df.to_csv(StockMoodAnalyzer.SRC_DIR "/" + filename + ".csv")


                df_analysis = pd.concat(data_frames) #, index = pd.data_range)

                tone_analysis_json_result = df_analysis.reset_index().to_dict() #####

                self.result_tone_reader.append(tone_analysis_json_result) # main-point



                full_df.rename(columns={'tone_id': 'Category'}, inplace=True)
                full_df = full_df.reset_index()
                del full_df['index']
                df_html = full_df.to_html()
                self.list_df_html.append(df_html)
                print full_df


                """
                print "Storing results data..."
                filename = self.stock_name
                date = datetime.now().strftime ("%Y%m%d")
                directory = "/Users/alparhanuguray/desktop/emontio_Web/data_formats/data_storage/"
                full_df.to_csv(directory + filename + "_" + date + ".csv")
                print "Data is stored."
                """

                print "----------- Tone Analysis is completed. ---------------"

            else:
                print "Scanned articles are irrelevant."



        try:

            print "AVERAGE VALUES FOR TONE ANALYZER DATA FRAME:"
            # Takes an average of the combined results.


            data_average = {'anger_avg' : [df_analysis.loc[df_analysis['tone_id'] == 'anger', 'score'].mean()],
            'disgust_avg' :  [df_analysis.loc[df_analysis['tone_id'] == 'disgust', 'score'].mean()],
            'fear_avg' : [df_analysis.loc[df_analysis['tone_id'] == 'fear', 'score'].mean()],
            'joy_avg' : [df_analysis.loc[df_analysis['tone_id'] == 'joy', 'score'].mean()],
            'sadness_avg' : [df_analysis.loc[df_analysis['tone_id'] == 'sadness', 'score'].mean()],
            'analytical_avg' : [df_analysis.loc[df_analysis['tone_id'] == 'analytical', 'score'].mean()],
            'confident_avg' : [df_analysis.loc[df_analysis['tone_id'] == 'confident', 'score'].mean()],
            'tentative_avg' : [df_analysis.loc[df_analysis['tone_id'] == 'tentative', 'score'].mean()],
            'openness_big5_avg' : [df_analysis.loc[df_analysis['tone_id'] == 'openness_big5', 'score'].mean()],
            'conscientiousness_big5_avg' : [df_analysis.loc[df_analysis['tone_id'] == 'conscientiousness_big5', 'score'].mean()],
            'extraversion_big5_avg' : [df_analysis.loc[df_analysis['tone_id'] == 'extraversion_big5', 'score'].mean()],
            'agreeableness_big5_avg' : [df_analysis.loc[df_analysis['tone_id'] == 'agreeableness_big5', 'score'].mean()],
            'neuroticism_big5_avg' : [df_analysis.loc[df_analysis['tone_id'] == 'neuroticism_big5', 'score'].mean()]}

            df_avg = pd.DataFrame(data = data_average).T

            average_tone_json_results = df_avg.to_dict() ######
            self.result_tone_reader.append(average_tone_json_results)

            print df_avg

        except:
            pass

        print "Time Elapsed: " , datetime.now() - startTime
        execution_time = datetime.now() - startTime
        self.list_time_elapsed.append(execution_time)

    def Entity_Extraction(self):

        print " ----------------------------"
        print "# STARTING ENTITY EXTRACTION:"
        print " ----------------------------"

        count = 0

        os.system("python templates/alchemyapi.py 32449e7b4f6b65f9ef5cfd84b7128a46440a9402")

        startTime = datetime.now()
        # Create the AlchemyAPI Object
        alchemyapi = AlchemyAPI()
        for paragraph in self.targeted_paragraphs:
            response = alchemyapi.entities('text', paragraph, {'sentiment': 1})

            if response['status'] == 'OK':

                print "DOCUMENT-LEVEL RESULTS:  "

                print "ARTICLE TITLE: " , self.article_title[len(self.article_title) - len(self.article_title) + count]
                print 'ARTICLE URL: ' , self.article_url[len(self.article_url) - len(self.article_url) + count]
                print "DATA FRAME: "
                count = count + 1

                for entity in response['entities']:

                    entity_text = entity['text']
                    entity_type = entity['type']
                    entity_relevance = entity['relevance']
                    entity_sentiment_type = entity['sentiment']['type']

                    if 'score' in entity['sentiment']:
                        entity_sentiment_score = entity['sentiment']['score']

                    df_entity_extraction = pd.DataFrame(data = {'text': [entity_text],
                                                         'type': [entity_type],
                                                         'relevance': [entity_relevance],
                                                         'sentiment': [entity_sentiment_type],
                                                         'sentiment_score': [entity_sentiment_score]})

                    print "***** ENTITY EXTRACTION RESULTS: *****"
                    print df_entity_extraction.T
                    df_transpose = df_entity_extraction.T


                    entity_json_results = df_transpose.to_dict() #######
                    self.result_entity_extraction.append(entity_json_results)

                else:
                    pass

            else:
                print 'Error in entity extraction call: ', response['statusInfo']

        print "----------- Entity Extraction is completed. ---------------"

        print "Time Elapsed: " , datetime.now() - startTime
        execution_time = datetime.now() - startTime
        self.list_time_elapsed.append(execution_time)


    def Sentiment_Analysis(self):

        print " ----------------------------"
        print "# STARTING SENTIMENT ANALYSIS:"
        print " ----------------------------"

        df_sentiment_combined = []

        startTime = datetime.now()
        count = 0
        # Create the AlchemyAPI Object
        alchemyapi = AlchemyAPI()
        for paragraph in self.targeted_paragraphs:
            response = alchemyapi.sentiment('text', paragraph)
            if response['status'] == 'OK':

                print '---------------------------------------'
                print "***** DOCUMENT SENTIMENT RESULTS: *****"
                print "DOCUMENT-LEVEL RESULTS:  "

                print "ARTICLE TITLE: " , self.article_title[len(self.article_title) - len(self.article_title) + count]
                print 'ARTICLE URL: ' , self.article_url[len(self.article_url) - len(self.article_url) + count]
                print "DATA FRAME: "

                count = count + 1

                data_sentiment = {'type': [response['docSentiment']['type']],
                                  'score': [response['docSentiment']['score']]}

                df_sentiment_analysis = pd.DataFrame(data = data_sentiment).T

                print df_sentiment_analysis

                sentiment_json_results= df_sentiment_analysis.to_dict() ########

                df_sentiment_combined.append(df_sentiment_analysis)

            else:
                print('Error in sentiment analysis call: ', response['statusInfo'])


        try:
            print "***** AVERAGE DOCUMENT SENTIMENT RESULTS: *****"
            df_sentiment_avg = pd.concat(df_sentiment_combined).T

            sentiment_avg_json_results = df_sentiment_avg.to_dict() ##########
            self.result_sentiment_analysis.append(sentiment_avg_json_results)

            print df_sentiment_avg

        except:
            pass

        try:
            sentiment_score = np.array(df_sentiment_avg)
            sentiment_score_even = sentiment_score[:, 0::2]
            sentiment_score_calculation = [float(i) for i in sentiment_score_even[0]]
            avg_sentiment_score = sum(sentiment_score_calculation)/len(sentiment_score_calculation)
            print "AVERAGE SENTIMENT SCORE =" , avg_sentiment_score

            average_sentiment_score = { "Average Sentiment Score" :  avg_sentiment_score}

            self.result_sentiment_analysis.append(average_sentiment_score)

        except:
            pass


        print "----------- Sentiment Analysis is completed. ---------------"

        print "Time Elapsed: " , datetime.now() - startTime
        execution_time = datetime.now() - startTime
        self.list_time_elapsed.append(execution_time)





def handle_form_submit(stock_id, stock_name, web_url):

    print 'emontio: handle_form_submit'

    analyzer = Emontio_Analyzer(stock_id, stock_name, web_url)
    analyzer.get_api_key()
    analyzer.scan_targeted_web()
    analyzer.Tone_Reader()
    analyzer.Entity_Extraction()
    analyzer.Sentiment_Analysis()

    return analyzer


def main():

    print 'emontio: running as executable'
    analyzer = Emontio_Analyzer(stock_id, stock_name, web_url)
    analyzer.get_api_key()
    analyzer.scan_targeted_web()
    analyzer.Tone_Reader()
    analyzer.Entity_Extraction()
    analyzer.Sentiment_Analysis()
    analyzer.time_elapsed()

    #complete_results = sys.stdout


if __name__ == '__main__':
    print '@@@@@@@' + str(sys.argv)
    main()
